"""Persists match results and recomputes them when their inputs change."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_matching_weights
from app.db.base import utcnow
from app.models.entities import CandidatePreference, CandidateProfile, Job, JobMatch, User
from app.repositories.jobs import visible_jobs_query
from app.schemas.jobs import MatchBrief
from app.services.matching.engine import ALGORITHM_VERSION, compute_match
from app.services.matching.facts import candidate_facts, job_facts
from app.utils.text import content_hash


def _profile_and_prefs(db: Session, user_id: uuid.UUID) -> tuple[CandidateProfile | None, CandidatePreference | None]:
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    prefs = db.scalar(select(CandidatePreference).where(CandidatePreference.user_id == user_id))
    return profile, prefs


def _prefs_key(prefs: CandidatePreference | None) -> Any:
    if prefs is None:
        return None
    return [
        prefs.desired_titles,
        prefs.preferred_locations,
        prefs.max_commute_km,
        str(prefs.remote_preference),
        prefs.employment_types,
        prefs.salary_min,
        prefs.salary_period,
        prefs.salary_currency,
        prefs.industries,
    ]


def input_hash(profile: CandidateProfile | None, prefs: CandidatePreference | None, job: Job) -> str:
    """Everything a score depends on. When any of it changes, the stored match is stale."""
    weights = get_matching_weights().model_dump()
    month = date.today().strftime("%Y-%m")  # ongoing positions add experience every month
    profile_key = (
        None if profile is None else [profile.content_hash, profile.headline, profile.city, profile.embedding_hash, profile.content]
    )
    job_key = [job.content_hash, job.updated_at.isoformat() if job.updated_at else None, job.embedding_hash]
    return content_hash([ALGORITHM_VERSION, weights, month, profile_key, _prefs_key(prefs), job_key])


def get_or_compute(db: Session, user: User, jobs: list[Job], *, commit: bool = True) -> dict[uuid.UUID, JobMatch]:
    profile, prefs = _profile_and_prefs(db, user.id)
    existing = {
        m.job_id: m for m in db.scalars(select(JobMatch).where(JobMatch.user_id == user.id, JobMatch.job_id.in_([j.id for j in jobs])))
    }
    weights = get_matching_weights()
    facts = None
    result: dict[uuid.UUID, JobMatch] = {}
    changed = False
    for job in jobs:
        digest = input_hash(profile, prefs, job)
        match = existing.get(job.id)
        if match is None or match.input_hash != digest:
            if facts is None:
                facts = candidate_facts(profile, prefs)
            computed = compute_match(facts, job_facts(job), weights)
            if match is None:
                match = JobMatch(user_id=user.id, job_id=job.id)
                db.add(match)
            match.score = computed["score"]
            match.result = computed
            match.algorithm_version = ALGORITHM_VERSION
            match.input_hash = digest
            match.calculated_at = utcnow()
            changed = True
        result[job.id] = match
    if changed and commit:
        db.commit()
    return result


def brief(match: JobMatch | None) -> MatchBrief | None:
    if match is None:
        return None
    r = match.result
    return MatchBrief(
        score=match.score,
        status=r.get("status", "ok"),
        matching_skills=[s["name"] for s in r.get("matching_skills", [])][:3],
        missing_required_skills=[s["name"] for s in r.get("missing_required_skills", [])][:3],
        strongest_factors=r.get("strongest_factors", []),
        eligibility=r.get("eligibility", {}).get("status", "unknown"),
    )


def recommendations(db: Session, user: User, limit: int = 10, min_score: int = 1) -> list[tuple[Job, JobMatch]]:
    jobs = list(db.scalars(visible_jobs_query().options(selectinload(Job.skills), selectinload(Job.company)).limit(1000)))
    matches = get_or_compute(db, user, jobs)
    ranked = [(job, matches[job.id]) for job in jobs if (matches[job.id].score or 0) >= min_score]
    ranked.sort(key=lambda pair: (pair[1].score or 0, pair[0].published_at or utcnow()), reverse=True)
    return ranked[:limit]


def recalculate_all(db: Session, user: User) -> int:
    jobs = list(db.scalars(visible_jobs_query().options(selectinload(Job.skills), selectinload(Job.company)).limit(1000)))
    db.query(JobMatch).filter(JobMatch.user_id == user.id).delete()
    db.flush()
    get_or_compute(db, user, jobs)
    return len(jobs)
