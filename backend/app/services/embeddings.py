"""Embeddings for semantic matching. Computed by the worker and cached on the row with a hash of the
embedded text, so they are only recomputed when the text changes."""

import logging

from sqlalchemy.orm import Session

from app.integrations.ai.base import AIError
from app.integrations.ai.factory import get_embeddings
from app.models.entities import CandidatePreference, CandidateProfile, Job
from app.schemas.profile import ProfileContent
from app.utils.text import content_hash

logger = logging.getLogger("talentflow.embeddings")


def profile_text(profile: CandidateProfile, prefs: CandidatePreference | None) -> str:
    content = ProfileContent.model_validate(profile.content or {})
    parts = [profile.headline or "", profile.summary or ""]
    parts += [f"{e.title}: {' '.join(e.bullets)} {e.description or ''}" for e in content.experiences]
    parts.append("Skills: " + ", ".join(content.skills))
    if prefs and prefs.desired_titles:
        parts.append("Desired roles: " + ", ".join(prefs.desired_titles))
    return "\n".join(p for p in parts if p.strip())[:6000]


def job_text(job: Job) -> str:
    parts = [job.title, job.description, *(job.responsibilities or []), "Skills: " + ", ".join(s.name for s in job.skills)]
    return "\n".join(p for p in parts if p)[:6000]


def refresh_profile_embedding(db: Session, profile: CandidateProfile, prefs: CandidatePreference | None) -> bool:
    provider = get_embeddings()
    text = profile_text(profile, prefs)
    if provider is None or len(text) < 20:
        return False
    digest = content_hash([provider.model, text])
    if profile.embedding_hash == digest:
        return False
    try:
        profile.embedding = provider.embed([f"search_document: {text}"])[0]
    except AIError as exc:
        logger.warning("Profile embedding failed: %s", exc.code)
        return False
    profile.embedding_hash = digest
    db.commit()
    return True


def refresh_job_embedding(db: Session, job: Job) -> bool:
    provider = get_embeddings()
    if provider is None:
        return False
    text = job_text(job)
    digest = content_hash([provider.model, text])
    if job.embedding_hash == digest:
        return False
    try:
        job.embedding = provider.embed([f"search_document: {text}"])[0]
    except AIError as exc:
        logger.warning("Job embedding failed: %s", exc.code)
        return False
    job.embedding_hash = digest
    db.commit()
    return True
