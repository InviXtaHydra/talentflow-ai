import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import case, func, literal_column, or_, select

from app.api.deps import AdminUser, DbSession
from app.core.errors import AppError, NotFoundError
from app.db.base import utcnow
from app.models.entities import (
    AIUsageRecord,
    Application,
    AuditLog,
    BackgroundTask,
    Company,
    CVDocument,
    CVVersion,
    Job,
    User,
    UserSession,
)
from app.models.enums import JobStatus, TaskStatus, UserRole
from app.schemas.common import Message, Page, page_count
from app.services.audit import audit
from app.services.job_ingestion import FeedBatch, ingest

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def stats(db: DbSession, _: AdminUser) -> dict:
    def count(model, *where) -> int:
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    since = utcnow() - timedelta(days=30)
    users_by_role = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
    ai = db.execute(
        select(
            AIUsageRecord.operation,
            func.count(),
            func.avg(AIUsageRecord.duration_ms),
            func.sum(case((AIUsageRecord.success.is_(True), 1), else_=0)),
        )
        .where(AIUsageRecord.created_at >= since)
        .group_by(AIUsageRecord.operation)
    ).all()
    day = func.date_trunc(literal_column("'day'"), User.created_at).label("day")
    signups = db.execute(select(day, func.count()).where(User.created_at >= since).group_by(day).order_by(day)).all()
    return {
        "users": {role.value: n for role, n in users_by_role.items()},
        "companies": count(Company),
        "jobs": {
            "published": count(Job, Job.status == JobStatus.PUBLISHED),
            "draft": count(Job, Job.status == JobStatus.DRAFT),
            "closed": count(Job, Job.status == JobStatus.CLOSED),
            "demo": count(Job, Job.is_demo.is_(True)),
        },
        "cv_documents": count(CVDocument),
        "cv_versions": count(CVVersion),
        "applications": count(Application),
        "active_sessions": count(UserSession, UserSession.expires_at > utcnow()),
        "tasks": {
            "queued": count(BackgroundTask, BackgroundTask.status == TaskStatus.QUEUED),
            "running": count(BackgroundTask, BackgroundTask.status == TaskStatus.RUNNING),
            "failed_30d": count(BackgroundTask, BackgroundTask.status == TaskStatus.FAILED, BackgroundTask.created_at >= since),
        },
        "ai_usage_30d": [{"operation": op, "calls": n, "avg_ms": round(avg or 0), "succeeded": int(ok or 0)} for op, n, avg, ok in ai],
        "signups_30d": [{"date": day.date().isoformat(), "count": n} for day, n in signups],
    }


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_demo: bool
    email_verified: bool
    created_at: datetime
    last_active_at: datetime | None


@router.get("/users", response_model=Page[AdminUserOut])
def users(db: DbSession, _: AdminUser, q: str | None = None, role: UserRole | None = None, page: int = 1) -> Page[AdminUserOut]:
    stmt = select(User)
    if q:
        stmt = stmt.where(or_(User.email.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")))
    if role:
        stmt = stmt.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(User.created_at.desc()).offset((max(page, 1) - 1) * 25).limit(25))
    items = [
        AdminUserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value,
            is_active=u.is_active,
            is_demo=u.is_demo,
            email_verified=u.email_verified_at is not None,
            created_at=u.created_at,
            last_active_at=u.last_active_at,
        )
        for u in rows
    ]
    return Page(items=items, total=total, page=page, page_size=25, pages=page_count(total, 25))


class UserStatusRequest(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}", response_model=Message)
def set_user_status(user_id: uuid.UUID, body: UserStatusRequest, db: DbSession, admin: AdminUser) -> Message:
    target = db.get(User, user_id)
    if target is None:
        raise NotFoundError("Gebruiker niet gevonden.")
    if target.id == admin.id:
        raise AppError("Je kunt je eigen account niet blokkeren.", code="self_action", status_code=409)
    target.is_active = body.is_active
    if not body.is_active:
        db.query(UserSession).filter(UserSession.user_id == target.id).delete()
    audit(db, "admin.user_status", actor_id=admin.id, target_type="user", target_id=target.id, details={"is_active": body.is_active})
    db.commit()
    return Message(message="Account geactiveerd." if body.is_active else "Account geblokkeerd en uitgelogd.")


class AdminJobOut(BaseModel):
    id: uuid.UUID
    title: str
    company_name: str
    status: str
    source: str
    is_demo: bool
    published_at: datetime | None
    created_at: datetime


@router.get("/jobs", response_model=Page[AdminJobOut])
def admin_jobs(db: DbSession, _: AdminUser, q: str | None = None, status: JobStatus | None = None, page: int = 1) -> Page[AdminJobOut]:
    stmt = select(Job, Company.name).join(Company, Company.id == Job.company_id)
    if q:
        stmt = stmt.where(or_(Job.title.ilike(f"%{q}%"), Company.name.ilike(f"%{q}%")))
    if status:
        stmt = stmt.where(Job.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(Job.created_at.desc()).offset((max(page, 1) - 1) * 25).limit(25)).all()
    items = [
        AdminJobOut(
            id=j.id,
            title=j.title,
            company_name=name,
            status=j.status.value,
            source=j.source.value,
            is_demo=j.is_demo,
            published_at=j.published_at,
            created_at=j.created_at,
        )
        for j, name in rows
    ]
    return Page(items=items, total=total, page=page, page_size=25, pages=page_count(total, 25))


@router.post("/jobs/{job_id}/close", response_model=Message)
def close_job(job_id: uuid.UUID, db: DbSession, admin: AdminUser) -> Message:
    job = db.get(Job, job_id)
    if job is None:
        raise NotFoundError("Vacature niet gevonden.")
    job.status = JobStatus.CLOSED
    job.closed_at = utcnow()
    audit(db, "admin.job_closed", actor_id=admin.id, target_type="job", target_id=job.id)
    db.commit()
    return Message(message="Vacature gesloten.")


class AuditOut(BaseModel):
    id: uuid.UUID
    action: str
    actor_user_id: uuid.UUID | None
    target_type: str | None
    target_id: str | None
    details: dict
    created_at: datetime


@router.get("/audit-logs", response_model=list[AuditOut])
def audit_logs(db: DbSession, _: AdminUser, action: str | None = None) -> list[AuditOut]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"{action}%"))
    return [AuditOut.model_validate(a, from_attributes=True) for a in db.scalars(stmt)]


@router.post("/job-feeds/import", summary="Import vacancies from an authorized feed (JSON in the FeedBatch format)")
def import_feed(body: FeedBatch, db: DbSession, admin: AdminUser) -> dict:
    company = db.get(Company, body.company_id)
    if company is None:
        raise NotFoundError("Bedrijf niet gevonden.")
    result = ingest(db, company, body.jobs, close_missing=body.close_missing)
    audit(db, "admin.feed_import", actor_id=admin.id, target_type="company", target_id=company.id, details=result)
    db.commit()
    return result
