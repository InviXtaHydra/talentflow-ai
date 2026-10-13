"""GDPR self-service: data export and account deletion (database rows and private files)."""

from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import verify_password
from app.db.base import utcnow
from app.integrations.storage.local import get_storage
from app.models.entities import (
    AIUsageRecord,
    Application,
    AssistantMessage,
    BackgroundTask,
    CandidatePreference,
    CandidateProfile,
    CompanyMembership,
    CVAnalysis,
    CVDocument,
    CVVersion,
    JobMatch,
    Notification,
    SavedJob,
    User,
    UserSession,
)
from app.models.enums import CompanyRole, TaskStatus
from app.services.audit import audit


def _rows(db: Session, model, user_id) -> list[dict[str, Any]]:
    out = []
    for row in db.scalars(select(model).where(model.user_id == user_id)):
        data = {
            c.name: getattr(row, c.name)
            for c in model.__table__.columns
            if c.name not in ("embedding", "storage_key", "token_hash", "csrf_token")
        }
        out.append(
            {
                k: (
                    v.isoformat()
                    if hasattr(v, "isoformat")
                    else (str(v) if v is not None and not isinstance(v, (int, float, bool, dict, list, str)) else v)
                )
                for k, v in data.items()
            }
        )
    return out


def export_data(db: Session, user: User) -> dict[str, Any]:
    audit(db, "privacy.export", actor_id=user.id, target_type="user", target_id=user.id)
    db.commit()
    return {
        "exported_at": utcnow().isoformat(),
        "account": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "locale": user.locale,
            "created_at": user.created_at.isoformat(),
            "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
        },
        "profile": _rows(db, CandidateProfile, user.id),
        "preferences": _rows(db, CandidatePreference, user.id),
        "cv_documents": _rows(db, CVDocument, user.id),
        "cv_versions": _rows(db, CVVersion, user.id),
        "cv_analyses": _rows(db, CVAnalysis, user.id),
        "job_matches": _rows(db, JobMatch, user.id),
        "saved_jobs": _rows(db, SavedJob, user.id),
        "applications": _rows(db, Application, user.id),
        "notifications": _rows(db, Notification, user.id),
        "assistant_messages": _rows(db, AssistantMessage, user.id),
        "sessions": _rows(db, UserSession, user.id),
        "ai_usage": _rows(db, AIUsageRecord, user.id),
        "company_memberships": _rows(db, CompanyMembership, user.id),
    }


def _sole_owner_companies(db: Session, user: User) -> list[str]:
    owned = db.scalars(
        select(CompanyMembership.company_id).where(CompanyMembership.user_id == user.id, CompanyMembership.role == CompanyRole.OWNER)
    )
    names = []
    for company_id in owned:
        owners = (
            db.scalar(
                select(func.count())
                .select_from(CompanyMembership)
                .where(CompanyMembership.company_id == company_id, CompanyMembership.role == CompanyRole.OWNER)
            )
            or 0
        )
        members = db.scalar(select(func.count()).select_from(CompanyMembership).where(CompanyMembership.company_id == company_id)) or 0
        if owners <= 1 and members > 1:
            names.append(str(company_id))
    return names


def delete_account(db: Session, user: User, password: str | None, *, verify: bool = True) -> None:
    if verify and not verify_password(password or "", user.password_hash):
        raise AuthenticationError("Je wachtwoord is onjuist.", code="invalid_credentials")
    if _sole_owner_companies(db, user):
        raise ConflictError(
            "Je bent de enige eigenaar van een bedrijf met andere leden. Maak eerst iemand anders eigenaar.", code="sole_owner"
        )
    keys = list(db.scalars(select(CVDocument.storage_key).where(CVDocument.user_id == user.id, CVDocument.storage_key.is_not(None))))
    db.execute(delete(BackgroundTask).where(BackgroundTask.user_id == user.id))
    audit(db, "privacy.account_deleted", actor_id=None, target_type="user", target_id=user.id)
    db.delete(user)  # cascades to every user-owned row (ON DELETE CASCADE)
    db.commit()
    storage = get_storage()
    for key in keys:
        storage.delete(key)


def _deleted(db: Session, statement: Any) -> int:
    return int(getattr(db.execute(statement), "rowcount", 0) or 0)


def apply_retention(db: Session) -> dict[str, int]:
    """Runs daily in the worker. Removes expired sessions/tokens, old operational records and, when
    configured, accounts that have been inactive for too long."""
    from app.models.entities import AuthToken

    settings = get_settings()
    now = utcnow()
    result = {
        "sessions": _deleted(db, delete(UserSession).where(UserSession.expires_at < now)),
        "tokens": _deleted(db, delete(AuthToken).where(AuthToken.expires_at < now - timedelta(days=1))),
    }
    cutoff = now - timedelta(days=settings.operational_log_retention_days)
    result["ai_usage"] = _deleted(db, delete(AIUsageRecord).where(AIUsageRecord.created_at < cutoff))
    result["tasks"] = _deleted(
        db,
        delete(BackgroundTask).where(
            BackgroundTask.finished_at < cutoff,
            BackgroundTask.status.in_([TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED]),
        ),
    )
    db.commit()
    deleted_accounts = 0
    if settings.inactive_account_retention_days > 0:
        inactive_cutoff = now - timedelta(days=settings.inactive_account_retention_days)
        for user in db.scalars(
            select(User).where(
                func.coalesce(User.last_active_at, User.created_at) < inactive_cutoff, User.is_demo.is_(False), User.role != "admin"
            )
        ).all():
            try:
                delete_account(db, user, None, verify=False)
                deleted_accounts += 1
            except ConflictError:
                db.rollback()
    result["inactive_accounts"] = deleted_accounts
    return result
