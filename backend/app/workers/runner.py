"""Background worker: executes queued tasks from the `background_tasks` table.

- Claims one task at a time with SELECT ... FOR UPDATE SKIP LOCKED (safe with several workers).
- Retries failed attempts with backoff, up to `max_attempts`.
- A task whose heartbeat stops (worker crashed or was restarted) is re-queued or failed.
- Runs the data-retention job once a day.

Start with:  python -m app.workers.runner
"""

import logging
import signal
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.db.base import utcnow
from app.db.session import SessionLocal
from app.integrations.ai.base import AIError, AINotConfiguredError
from app.models.entities import BackgroundTask, CandidatePreference, CandidateProfile, CVDocument, Job, User
from app.models.enums import TaskStatus
from app.services import embeddings, privacy_service
from app.services.cv import analysis, documents, optimizer

logger = logging.getLogger("talentflow.worker")
POLL_SECONDS = 1.0
RETRY_BACKOFF_SECONDS = 20

Progress = Callable[[int, str], None]


# ── task handlers ────────────────────────────────────────────────────────────


def _extract_cv(db: Session, task: BackgroundTask, progress: Progress) -> dict[str, Any]:
    documents.run_extraction(db, uuid.UUID(task.payload["cv_id"]), progress)
    return {"cv_id": task.payload["cv_id"]}


def _analyze_cv(db: Session, task: BackgroundTask, progress: Progress) -> dict[str, Any]:
    user = db.get(User, task.user_id)
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == task.user_id))
    if user is None or profile is None:
        raise AppError("Profiel niet gevonden.")
    cv_id = uuid.UUID(task.payload["cv_id"]) if task.payload.get("cv_id") else None
    cv_text = None
    if cv_id:
        document = db.get(CVDocument, cv_id)
        cv_text = document.extracted_text if document and document.user_id == user.id else None
    progress(30, "Cv beoordelen")
    result = analysis.run_analysis(db, user, profile, cv_id, cv_text)
    return {"analysis_id": str(result.id)}


def _optimize_cv(db: Session, task: BackgroundTask, progress: Progress) -> dict[str, Any]:
    payload = task.payload
    source = uuid.UUID(payload["source_version_id"]) if payload.get("source_version_id") else None
    optimizer.run(db, uuid.UUID(payload["version_id"]), uuid.UUID(payload["job_id"]), source, progress)
    return {"optimization_id": payload["version_id"]}


def _embed_profile(db: Session, task: BackgroundTask, progress: Progress) -> dict[str, Any]:
    user_id = uuid.UUID(task.payload["user_id"])
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    prefs = db.scalar(select(CandidatePreference).where(CandidatePreference.user_id == user_id))
    changed = embeddings.refresh_profile_embedding(db, profile, prefs) if profile else False
    return {"updated": changed}


def _embed_job(db: Session, task: BackgroundTask, progress: Progress) -> dict[str, Any]:
    job = db.get(Job, uuid.UUID(task.payload["job_id"]))
    return {"updated": embeddings.refresh_job_embedding(db, job) if job else False}


HANDLERS: dict[str, Callable[[Session, BackgroundTask, Progress], dict[str, Any]]] = {
    "extract_cv": _extract_cv,
    "analyze_cv": _analyze_cv,
    "optimize_cv": _optimize_cv,
    "embed_profile": _embed_profile,
    "embed_job": _embed_job,
}


def _on_final_failure(db: Session, task: BackgroundTask, message: str) -> None:
    if task.type == "optimize_cv":
        optimizer.mark_failed(db, uuid.UUID(task.payload["version_id"]), message)
    elif task.type == "extract_cv":
        from app.models.enums import ExtractionStatus

        document = db.get(CVDocument, uuid.UUID(task.payload["cv_id"]))
        if document and document.extraction_status in (ExtractionStatus.PENDING, ExtractionStatus.PROCESSING):
            document.extraction_status = ExtractionStatus.FAILED
            document.extraction_error = message[:500]
            db.commit()


# ── queue mechanics ──────────────────────────────────────────────────────────


def claim_next(db: Session) -> BackgroundTask | None:
    task = db.scalar(
        select(BackgroundTask)
        .where(BackgroundTask.status == TaskStatus.QUEUED, BackgroundTask.run_after <= utcnow())
        .order_by(BackgroundTask.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if task is None:
        db.rollback()
        return None
    task.status = TaskStatus.RUNNING
    task.attempts += 1
    task.started_at = task.heartbeat_at = utcnow()
    task.error_code = task.error_message = None
    db.commit()
    return task


def recover_stalled(db: Session) -> int:
    """Running tasks without a heartbeat for longer than their timeout: re-queue or fail them."""
    now = utcnow()
    recovered = 0
    for task in db.scalars(select(BackgroundTask).where(BackgroundTask.status == TaskStatus.RUNNING).with_for_update(skip_locked=True)):
        last = task.heartbeat_at or task.started_at or task.created_at
        if now - last < timedelta(seconds=task.timeout_seconds + 30):
            continue
        recovered += 1
        if task.attempts < task.max_attempts:
            task.status = TaskStatus.QUEUED
            task.run_after = now
            task.progress_message = "Opnieuw ingepland na een onderbreking"
        else:
            task.status = TaskStatus.FAILED
            task.error_code = "interrupted"
            task.error_message = "De taak werd onderbroken. Probeer het opnieuw."
            task.finished_at = now
            task.idempotency_key = None
            _on_final_failure(db, task, task.error_message)
    db.commit()
    return recovered


def execute(task_id: uuid.UUID) -> None:
    """Runs one claimed task in its own database session."""
    with SessionLocal() as db:
        task = db.get(BackgroundTask, task_id)
        if task is None:
            return
        handler = HANDLERS.get(task.type)

        def progress(percent: int, message: str) -> None:
            with SessionLocal() as side:
                side.execute(
                    update(BackgroundTask)
                    .where(BackgroundTask.id == task_id)
                    .values(progress=percent, progress_message=message[:200], heartbeat_at=utcnow())
                )
                side.commit()

        try:
            if handler is None:
                raise AppError(f"Unknown task type {task.type}")
            result = handler(db, task, progress)
            db.refresh(task)
            task.status = TaskStatus.SUCCEEDED
            task.result = result
            task.progress = 100
            task.finished_at = utcnow()
            task.idempotency_key = None
            db.commit()
            logger.info("Task %s (%s) succeeded", task.id, task.type)
        except Exception as exc:  # every failure is recorded on the task
            db.rollback()
            task = db.get(BackgroundTask, task_id)
            assert task is not None
            retryable = not isinstance(exc, AINotConfiguredError) and isinstance(exc, (AIError, OSError))
            if isinstance(exc, AIError):
                code, message = exc.code, exc.user_message
            elif isinstance(exc, AppError):
                code, message = exc.code, exc.message
            else:
                code, message = "internal_error", "Er ging iets mis bij het verwerken. Probeer het opnieuw."
                logger.exception("Task %s (%s) crashed", task.id, task.type)
            if retryable and task.attempts < task.max_attempts:
                task.status = TaskStatus.QUEUED
                task.run_after = utcnow() + timedelta(seconds=RETRY_BACKOFF_SECONDS * task.attempts)
                task.progress_message = "Nieuwe poging volgt"
                logger.warning("Task %s (%s) failed with %s, retrying", task.id, task.type, code)
            else:
                task.status = TaskStatus.FAILED
                task.finished_at = utcnow()
                task.idempotency_key = None
                logger.warning("Task %s (%s) failed with %s", task.id, task.type, code)
                _on_final_failure(db, task, message)
            task.error_code, task.error_message = code, message[:500]
            db.commit()


def run_once(executor: ThreadPoolExecutor | None = None) -> bool:
    """Claim and run a single task. Returns False when the queue was empty."""
    with SessionLocal() as db:
        task = claim_next(db)
        if task is None:
            return False
        task_id, timeout = task.id, task.timeout_seconds
    if executor is None:
        execute(task_id)
        return True
    future = executor.submit(execute, task_id)
    try:
        future.result(timeout=timeout)
    except FutureTimeout:
        # The thread can't be killed; mark the task so the user isn't left waiting. Provider calls have their own timeouts.
        with SessionLocal() as db:
            task = db.get(BackgroundTask, task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.FAILED
                task.error_code = "timeout"
                task.error_message = "Dit duurde te lang. Probeer het opnieuw."
                task.finished_at = utcnow()
                task.idempotency_key = None
                _on_final_failure(db, task, task.error_message)
                db.commit()
    return True


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Worker started (AI provider: %s)", settings.ai_provider)
    stopping = False

    def stop(*_: object) -> None:
        nonlocal stopping
        stopping = True
        logger.info("Worker stopping after the current task")

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    last_recovery = last_retention = 0.0
    with ThreadPoolExecutor(max_workers=1) as executor:
        while not stopping:
            now = time.monotonic()
            if now - last_recovery > 30:
                with SessionLocal() as db:
                    if recovered := recover_stalled(db):
                        logger.info("Recovered %d interrupted task(s)", recovered)
                last_recovery = now
            if now - last_retention > 86400:
                with SessionLocal() as db:
                    logger.info("Retention: %s", privacy_service.apply_retention(db))
                last_retention = now
            try:
                if not run_once(executor):
                    time.sleep(POLL_SECONDS)
            except Exception:
                logger.exception("Worker loop error")
                time.sleep(5)


if __name__ == "__main__":
    main()
