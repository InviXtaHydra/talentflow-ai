"""Vacancy-specific CV optimization ("Optimaliseer mijn cv voor deze vacature").

Flow: start() validates access and queues a background task → run() (in the worker) gathers the source,
analyses the gap, asks the language model for a tailored CV, assembles + fact-checks it, recomputes the
match with the same engine and stores everything as a new CV version. The source CV is never modified."""

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_matching_weights, get_settings
from app.core.errors import AppError, NotFoundError
from app.core.rate_limit import rate_limiter
from app.integrations.ai.base import AINotConfiguredError
from app.integrations.ai.factory import llm_configured
from app.integrations.ai.prompts import CV_OPTIMIZATION, LANGUAGE_NAMES
from app.models.entities import BackgroundTask, CandidateProfile, CVVersion, Job, User
from app.models.enums import CVVersionKind, CVVersionStatus, JobStatus, TaskStatus
from app.schemas.cv import ChangeNote, CVContent, GapAnalysis, OptimizationReport, OptimizerOutput, ReviewItem
from app.services import ai_service, tasks
from app.services.audit import audit
from app.services.candidate_service import get_preferences, get_profile
from app.services.cv.content import contact_for, profile_to_cv_content
from app.services.cv.factcheck import assemble, describe_changes
from app.services.job_service import get_job
from app.services.matching.engine import compute_match
from app.services.matching.facts import candidate_facts, cv_candidate_facts, job_facts
from app.services.notifications import notify
from app.utils.skills import normalize_skill, split_skills, text_mentions_skill

logger = logging.getLogger("talentflow.optimizer")


def _source_version(db: Session, user: User, source_version_id: uuid.UUID | None) -> CVVersion | None:
    if source_version_id is None:
        return None
    version = db.get(CVVersion, source_version_id)
    if version is None or version.user_id != user.id or version.status != CVVersionStatus.READY:
        raise NotFoundError("Bron-cv niet gevonden.")
    return version


def _profile_has_content(profile: CandidateProfile) -> bool:
    content = profile.content or {}
    return bool(content.get("experiences") or content.get("skills") or profile.summary)


def start(
    db: Session, user: User, job_id: uuid.UUID, *, source_version_id: uuid.UUID | None, language: str | None, template: str
) -> tuple[CVVersion, BackgroundTask | None]:
    job = get_job(db, job_id)
    if job.status != JobStatus.PUBLISHED:
        raise AppError("Deze vacature staat niet (meer) open.", code="job_not_open", status_code=409)
    profile = get_profile(db, user.id)
    source = _source_version(db, user, source_version_id)
    if source is None and not _profile_has_content(profile):
        raise AppError(
            "Vul eerst je profiel aan of upload je cv, zodat er iets is om te optimaliseren.", code="profile_empty", status_code=409
        )
    simulated = not llm_configured()
    if simulated and not (profile.is_demo and job.is_demo):
        # Without a configured model only the seeded demo records get a (clearly labelled) simulated result.
        raise AINotConfiguredError("not configured")
    rate_limiter.hit(f"optimize:{user.id}", limit=20, window_seconds=3600)

    language = language or (source.language if source else None) or "nl"
    key = f"optimize:{user.id}:{job.id}:{source_version_id or 'profile'}:{language}"
    running = db.scalar(select(BackgroundTask).where(BackgroundTask.idempotency_key == key, BackgroundTask.status.in_(tasks.ACTIVE)))
    if running is not None:
        version = db.get(CVVersion, uuid.UUID(running.payload["version_id"]))
        if version is not None:
            return version, running

    version = CVVersion(
        user_id=user.id,
        source_cv_id=source.source_cv_id if source else None,
        target_job_id=job.id,
        kind=CVVersionKind.OPTIMIZED,
        status=CVVersionStatus.GENERATING,
        title=f"{job.title} – {job.company.name}"[:200],
        language=language,
        template=template,
        is_simulated=simulated,
    )
    db.add(version)
    db.flush()
    payload = {
        "version_id": str(version.id),
        "job_id": str(job.id),
        "source_version_id": str(source_version_id) if source_version_id else None,
    }
    task = tasks.enqueue(
        db,
        "optimize_cv",
        user_id=user.id,
        payload=payload,
        idempotency_key=key,
        max_attempts=2,
        timeout_seconds=int(get_settings().ai_timeout_seconds) * 2 + 60,
        commit=False,
    )
    audit(db, "cv.optimize_requested", actor_id=user.id, target_type="cv_version", target_id=version.id, details={"job_id": str(job.id)})
    db.commit()
    return version, task


# ── worker side ──────────────────────────────────────────────────────────────


def _gap(source: CVContent, job: Job) -> GapAnalysis:
    source_text = " ".join(
        [source.summary or "", *(b.text for e in source.experiences for b in e.bullets), *(e.title for e in source.experiences)]
    )
    profile_skills = {normalize_skill(s) for s in split_skills(source.skills)} | {
        normalize_skill(t) for p in source.projects for t in p.technologies
    }
    matching, missing_required, missing_preferred, missing_keywords = [], [], [], []
    for skill in job.skills:
        listed = skill.normalized_name in profile_skills
        in_text = text_mentions_skill(source_text, skill.normalized_name)
        if listed or in_text:
            matching.append(skill.name)
            if listed and not in_text:
                # The skill is on the list but no experience shows it: a candidate for clearer wording.
                missing_keywords.append(skill.name)
        elif skill.is_required:
            missing_required.append(skill.name)
        else:
            missing_preferred.append(skill.name)
    relevant = [
        e.source_id
        for e in source.experiences
        if e.source_id
        and any(text_mentions_skill(" ".join([e.title, *(b.text for b in e.bullets)]), s.normalized_name) for s in job.skills)
    ]
    return GapAnalysis(
        matching_skills=matching,
        missing_required_skills=missing_required,
        missing_preferred_skills=missing_preferred,
        keywords_missing_from_cv=missing_keywords,
        relevant_experience_ids=relevant,
    )


def _prompt(source: CVContent, job: Job, gap: GapAnalysis) -> str:
    profile = {
        "headline": source.headline,
        "summary": source.summary,
        "experiences": [
            {
                "id": e.source_id,
                "title": e.title,
                "employer": e.employer,
                "start": e.start,
                "end": e.end,
                "current": e.is_current,
                "bullets": [b.text for b in e.bullets],
            }
            for e in source.experiences
        ],
        "projects": [
            {"id": p.source_id, "name": p.name, "description": p.description, "technologies": p.technologies} for p in source.projects
        ],
        "education": [{"id": e.source_id, "degree": e.degree, "institution": e.institution} for e in source.education],
        "certifications": [{"id": c.source_id, "name": c.name} for c in source.certifications],
        "skills": source.skills,
    }
    vacancy = {
        "title": job.title,
        "company": job.company.name,
        "description": job.description[:5000],
        "responsibilities": job.responsibilities,
        "qualifications": job.qualifications,
        "required_skills": [s.name for s in job.skills if s.is_required],
        "preferred_skills": [s.name for s in job.skills if not s.is_required],
    }
    return (
        f"<profile>\n{json.dumps(profile, ensure_ascii=False)}\n</profile>\n\n"
        f"<vacancy>\n{json.dumps(vacancy, ensure_ascii=False)}\n</vacancy>\n\n"
        f"Gap analysis computed by the platform (facts, not suggestions to invent): {gap.model_dump_json()}\n"
        "Return the tailored CV as JSON."
    )


def _demo_output(source: CVContent, job: Job, gap: GapAnalysis) -> OptimizerOutput:
    """Deterministic, rule-based tailoring used only for seeded demo records when no model is configured.
    It reorders by relevance and keeps the original wording; the result is labelled as simulated."""
    job_keys = [s.normalized_name for s in job.skills]

    def relevance(texts: list[str]) -> int:
        joined = " ".join(texts)
        return sum(1 for k in job_keys if text_mentions_skill(joined, k))

    experiences = sorted(source.experiences, key=lambda e: relevance([e.title, *(b.text for b in e.bullets)]), reverse=True)
    skills = sorted(source.skills, key=lambda s: (normalize_skill(s) not in job_keys, source.skills.index(s)))
    return OptimizerOutput(
        headline=source.headline,
        summary=source.summary or "",
        summary_source_refs=[],
        experience_order=[e.source_id for e in experiences if e.source_id],
        experiences=[],
        skills=skills,
        project_order=[
            p.source_id
            for p in sorted(source.projects, key=lambda p: relevance([p.name, p.description or "", *p.technologies]), reverse=True)
            if p.source_id
        ],
        projects=[],
        emphasized_keywords=gap.matching_skills[:8],
        changes=[
            ChangeNote(section="experience", description="Werkervaring gesorteerd op relevantie voor deze vacature."),
            ChangeNote(section="skills", description="Vaardigheden die de vacature vraagt, staan nu bovenaan."),
        ],
        questions=[],
    )


def _match(facts, job: Job) -> dict[str, Any]:
    return compute_match(facts, job_facts(job, use_embedding=False), get_matching_weights())


def run(db: Session, version_id: uuid.UUID, job_id: uuid.UUID, source_version_id: uuid.UUID | None, progress) -> None:
    version = db.get(CVVersion, version_id)
    if version is None:
        return
    user = db.get(User, version.user_id)
    job = get_job(db, job_id)
    assert user is not None
    profile = get_profile(db, user.id)
    prefs = get_preferences(db, user.id)

    progress(10, "Bronprofiel en vacature verzamelen")
    if source_version_id:
        source_row = db.get(CVVersion, source_version_id)
        if source_row is None or source_row.user_id != user.id or not source_row.content:
            raise NotFoundError("Bron-cv niet gevonden.")
        source = CVContent.model_validate(source_row.content)
        source = source.model_copy(update={"contact": contact_for(user, profile)})
    else:
        source = profile_to_cv_content(user, profile)
    version.source_snapshot = source.model_dump(mode="json")

    progress(20, "Verschillen met de vacature analyseren")
    gap = _gap(source, job)
    base_facts = candidate_facts(profile, prefs, use_embedding=False)
    match_before = _match(cv_candidate_facts(source, base_facts), job)

    progress(35, "Cv herschrijven voor deze vacature")
    if version.is_simulated:
        output = _demo_output(source, job, gap)
        provider, model = "demo", "rule-based-demo"
    else:
        language_name = LANGUAGE_NAMES.get(version.language, "Dutch")
        output, provider, model = ai_service.generate(
            db,
            user_id=user.id,
            operation="cv_optimization",
            system=CV_OPTIMIZATION.replace("{language}", language_name),
            user=_prompt(source, job, gap),
            schema=OptimizerOutput,
            temperature=0.3,
        )

    progress(80, "Feiten controleren tegen je profiel")
    tailored, review = assemble(source, output, [s.name for s in job.skills])
    match_after = _match(cv_candidate_facts(tailored, base_facts), job)

    questions = list(output.questions)
    for skill in gap.missing_required_skills[:5]:
        review.append(
            ReviewItem(
                kind="gap",
                section="skills",
                text=skill,
                reason="Gevraagd in de vacature maar niet gevonden in je profiel. Voeg het alleen toe als je deze ervaring echt hebt.",
            )
        )
    report = OptimizationReport(
        changes=describe_changes(source, tailored, output.changes, version.language),
        emphasized_keywords=[k for k in output.emphasized_keywords if k][:15],
        questions=questions[:8],
        review_items=review,
        gap=gap,
        target_language=version.language,
    )
    version.content = tailored.model_dump(mode="json")
    version.generated_content = version.content
    version.optimization = report.model_dump(mode="json")
    version.match_before = match_before
    version.match_after = match_after
    version.provider, version.model = provider, model
    version.status = CVVersionStatus.READY
    version.error_message = None
    notify(
        db,
        user.id,
        "cv_optimized",
        f"Je cv voor ‘{job.title}’ is klaar",
        "Bekijk de wijzigingen en controleer de inhoud voor je hem downloadt.",
        f"/cv/optimizations/{version.id}",
    )
    db.commit()
    progress(100, "Klaar")


def mark_failed(db: Session, version_id: uuid.UUID, message: str) -> None:
    version = db.get(CVVersion, version_id)
    if version is not None and version.status == CVVersionStatus.GENERATING:
        version.status = CVVersionStatus.FAILED
        version.error_message = message[:500]
        db.commit()


def regenerate(db: Session, user: User, version_id: uuid.UUID) -> tuple[CVVersion, BackgroundTask | None]:
    version = db.get(CVVersion, version_id)
    if version is None or version.user_id != user.id or version.kind != CVVersionKind.OPTIMIZED or version.target_job_id is None:
        raise NotFoundError("Geoptimaliseerd cv niet gevonden.")
    return start(db, user, version.target_job_id, source_version_id=None, language=version.language, template=version.template)


def active_task(db: Session, version: CVVersion) -> BackgroundTask | None:
    return db.scalar(
        select(BackgroundTask)
        .where(BackgroundTask.type == "optimize_cv", BackgroundTask.payload["version_id"].astext == str(version.id))
        .order_by(BackgroundTask.created_at.desc())
    )


def task_failed_message(task: BackgroundTask | None) -> str | None:
    if task and task.status == TaskStatus.FAILED:
        return task.error_message
    return None
