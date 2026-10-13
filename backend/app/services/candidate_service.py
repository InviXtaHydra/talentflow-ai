import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.base import utcnow
from app.models.entities import CandidatePreference, CandidateProfile, User
from app.schemas.candidate import CandidateProfileOut, CandidateProfileUpdate, PreferencesIn
from app.schemas.profile import ProfileContent
from app.services import tasks
from app.utils.text import content_hash


def get_profile(db: Session, user_id: uuid.UUID) -> CandidateProfile:
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    if profile is None:
        raise NotFoundError("Profiel niet gevonden.")
    return profile


def get_preferences(db: Session, user_id: uuid.UUID) -> CandidatePreference:
    prefs = db.scalar(select(CandidatePreference).where(CandidatePreference.user_id == user_id))
    if prefs is None:
        prefs = CandidatePreference(user_id=user_id)
        db.add(prefs)
        db.commit()
    return prefs


def profile_out(user: User, profile: CandidateProfile) -> CandidateProfileOut:
    return CandidateProfileOut(
        id=profile.id,
        full_name=user.full_name,
        email=user.email,
        headline=profile.headline,
        summary=profile.summary,
        phone=profile.phone,
        city=profile.city,
        linkedin_url=profile.linkedin_url,
        website_url=profile.website_url,
        content=ProfileContent.model_validate(profile.content or {}),
        onboarding_completed_at=profile.onboarding_completed_at,
        confirmed_at=profile.confirmed_at,
        updated_at=profile.updated_at,
        is_demo=profile.is_demo,
    )


def _schedule_embedding(db: Session, user_id: uuid.UUID) -> None:
    tasks.enqueue(
        db,
        "embed_profile",
        user_id=user_id,
        payload={"user_id": str(user_id)},
        idempotency_key=f"embed_profile:{user_id}",
        max_attempts=3,
        timeout_seconds=120,
        commit=False,
    )


def update_profile(db: Session, user: User, body: CandidateProfileUpdate) -> CandidateProfile:
    profile = get_profile(db, user.id)
    data = body.model_dump(exclude_unset=True, exclude={"content", "complete_onboarding"})
    for key, value in data.items():
        setattr(profile, key, value)
    if body.content is not None:
        profile.content = body.content.model_dump(mode="json")
        profile.confirmed_at = utcnow()
    profile.content_hash = content_hash([profile.headline, profile.summary, profile.city, profile.content])
    if body.complete_onboarding and profile.onboarding_completed_at is None:
        profile.onboarding_completed_at = utcnow()
    _schedule_embedding(db, user.id)
    db.commit()
    return profile


def update_preferences(db: Session, user: User, body: PreferencesIn) -> CandidatePreference:
    prefs = get_preferences(db, user.id)
    data = body.model_dump()
    data["employment_types"] = [str(t) for t in body.employment_types]
    for key, value in data.items():
        setattr(prefs, key, value)
    _schedule_embedding(db, user.id)
    db.commit()
    return prefs
