"""Background tasks, stored in PostgreSQL and executed by the worker (app/workers/runner.py)."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.entities import BackgroundTask
from app.models.enums import TaskStatus

ACTIVE = (TaskStatus.QUEUED, TaskStatus.RUNNING)


def enqueue(
    db: Session,
    type_: str,
    *,
    user_id: uuid.UUID | None,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
    max_attempts: int = 2,
    timeout_seconds: int = 600,
    commit: bool = True,
) -> BackgroundTask:
    """Queue a task. With an idempotency key, an identical task that is still queued/running is returned
    instead of starting a second one (protects against double clicks and page refreshes)."""
    if idempotency_key:
        existing = db.scalar(select(BackgroundTask).where(BackgroundTask.idempotency_key == idempotency_key))
        if existing is not None:
            if existing.status in ACTIVE:
                return existing
            # A finished task frees the key so the action can run again.
            existing.idempotency_key = None
            db.flush()
    task = BackgroundTask(
        type=type_,
        user_id=user_id,
        payload=payload,
        idempotency_key=idempotency_key,
        max_attempts=max_attempts,
        timeout_seconds=timeout_seconds,
    )
    db.add(task)
    try:
        if commit:
            db.commit()
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(BackgroundTask).where(BackgroundTask.idempotency_key == idempotency_key))
        if existing is None:
            raise
        return existing
    return task


def get_for_user(db: Session, task_id: uuid.UUID, user_id: uuid.UUID) -> BackgroundTask:
    task = db.get(BackgroundTask, task_id)
    if task is None or task.user_id != user_id:
        raise NotFoundError("Taak niet gevonden.")
    return task


def cancel(db: Session, task: BackgroundTask) -> None:
    if task.status == TaskStatus.QUEUED:
        task.status = TaskStatus.CANCELLED
        task.idempotency_key = None
        db.commit()
