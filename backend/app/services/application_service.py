import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.db.base import utcnow
from app.models.entities import (
    Application,
    ApplicationStatusHistory,
    CandidateProfile,
    CompanyMembership,
    CVVersion,
    Job,
    User,
)
from app.models.enums import ApplicationChannel, ApplicationStatus, CVVersionStatus, JobStatus, UserRole
from app.schemas.applications import (
    CANDIDATE_TRACKING_STATUSES,
    ApplicantOut,
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    EmployerStatusUpdate,
    StatusHistoryOut,
)
from app.services import job_service
from app.services.audit import audit
from app.services.company_service import member_company_ids, require_member
from app.services.matching import service as matching
from app.services.notifications import notify

STATUS_LABELS = {
    "saved": "Bewaard",
    "ready_to_apply": "Klaar om te solliciteren",
    "applied": "Gesolliciteerd",
    "in_review": "In behandeling",
    "interview": "Gesprek",
    "offer": "Aanbod",
    "rejected": "Afgewezen",
    "withdrawn": "Ingetrokken",
}


def _history(application: Application) -> list[StatusHistoryOut]:
    return [
        StatusHistoryOut(
            from_status=h.from_status.value if h.from_status else None,
            to_status=h.to_status.value,
            changed_by_role=h.changed_by_role,
            note=h.note,
            created_at=h.created_at,
        )
        for h in application.history
    ]


def _change_status(db: Session, application: Application, new: ApplicationStatus, actor: User, note: str | None) -> None:
    if application.status == new:
        return
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=application.status,
            to_status=new,
            changed_by_user_id=actor.id,
            changed_by_role=actor.role.value,
            note=note,
        )
    )
    application.status = new
    if new == ApplicationStatus.APPLIED and application.applied_at is None:
        application.applied_at = utcnow()


def application_out(application: Application) -> ApplicationOut:
    return ApplicationOut(
        id=application.id,
        job=job_service.summary(application.job),
        status=application.status,
        channel=application.channel,
        cv_version_id=application.cv_version_id,
        cv_version_title=application.cv_version.title if application.cv_version else None,
        notes=application.notes,
        cover_letter=application.cover_letter,
        applied_at=application.applied_at,
        created_at=application.created_at,
        updated_at=application.updated_at,
        history=_history(application),
    )


def _load(db: Session, application_id: uuid.UUID) -> Application | None:
    return db.scalar(
        select(Application)
        .where(Application.id == application_id)
        .options(
            selectinload(Application.job).selectinload(Job.skills),
            selectinload(Application.job).selectinload(Job.company),
            selectinload(Application.history),
            selectinload(Application.cv_version),
            selectinload(Application.user),
        )
    )


def create(db: Session, user: User, body: ApplicationCreate) -> Application:
    job = job_service.get_visible_job(db, user, body.job_id)
    existing = db.scalar(select(Application).where(Application.user_id == user.id, Application.job_id == job.id))
    if existing is not None:
        raise ConflictError(
            "Je volgt deze vacature al in je sollicitaties.", code="application_exists", details={"application_id": str(existing.id)}
        )
    cv_version = None
    if body.cv_version_id:
        cv_version = db.get(CVVersion, body.cv_version_id)
        if cv_version is None or cv_version.user_id != user.id or cv_version.status != CVVersionStatus.READY:
            raise NotFoundError("Cv-versie niet gevonden.")
    status = ApplicationStatus(body.status)
    if body.channel == ApplicationChannel.PLATFORM:
        if job.status != JobStatus.PUBLISHED:
            raise AppError("Deze vacature staat niet meer open.", code="job_not_open", status_code=409)
        if cv_version is None:
            raise AppError("Kies het cv dat je wilt meesturen.", code="cv_required", status_code=422)
        if not body.share_consent:
            raise AppError("Geef toestemming om je cv met deze werkgever te delen.", code="consent_required", status_code=422)
        status = ApplicationStatus.APPLIED
    application = Application(
        user_id=user.id,
        job_id=job.id,
        cv_version_id=cv_version.id if cv_version else None,
        status=status,
        channel=body.channel,
        notes=body.notes,
        cover_letter=body.cover_letter if body.channel == ApplicationChannel.PLATFORM else None,
        applied_at=utcnow() if status == ApplicationStatus.APPLIED else None,
        shared_with_employer_at=utcnow() if body.channel == ApplicationChannel.PLATFORM else None,
    )
    db.add(application)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Je volgt deze vacature al in je sollicitaties.", code="application_exists") from exc
    db.add(
        ApplicationStatusHistory(
            application_id=application.id, from_status=None, to_status=status, changed_by_user_id=user.id, changed_by_role=user.role.value
        )
    )
    if body.channel == ApplicationChannel.PLATFORM:
        members = db.scalars(select(CompanyMembership.user_id).where(CompanyMembership.company_id == job.company_id))
        for member_id in members:
            notify(
                db,
                member_id,
                "application_received",
                f"Nieuwe sollicitatie voor ‘{job.title}’",
                None,
                f"/employer/applications/{application.id}",
            )
        audit(db, "application.submitted", actor_id=user.id, target_type="application", target_id=application.id)
    db.commit()
    loaded = _load(db, application.id)
    assert loaded is not None
    return loaded


def list_mine(db: Session, user: User) -> list[Application]:
    ids = db.scalars(select(Application.id).where(Application.user_id == user.id).order_by(Application.updated_at.desc()))
    return [a for a in (_load(db, i) for i in ids) if a is not None]


def get_mine(db: Session, user: User, application_id: uuid.UUID) -> Application:
    application = _load(db, application_id)
    if application is None or application.user_id != user.id:
        raise NotFoundError("Sollicitatie niet gevonden.")
    return application


def update_mine(db: Session, user: User, application_id: uuid.UUID, body: ApplicationUpdate) -> Application:
    application = get_mine(db, user, application_id)
    if body.notes is not None:
        application.notes = body.notes
    if body.status is not None and body.status != application.status:
        if application.channel == ApplicationChannel.PLATFORM and body.status != ApplicationStatus.WITHDRAWN:
            raise PermissionDeniedError(
                "De status van een sollicitatie via het platform wordt door de werkgever bijgewerkt. Je kunt ze wel intrekken."
            )
        if body.status not in CANDIDATE_TRACKING_STATUSES:
            raise AppError("Ongeldige status.", code="invalid_status", status_code=422)
        if application.status == ApplicationStatus.WITHDRAWN and application.channel == ApplicationChannel.PLATFORM:
            raise AppError("Een ingetrokken sollicitatie kan niet opnieuw geopend worden.", code="invalid_status", status_code=409)
        _change_status(db, application, body.status, user, body.note)
        if application.channel == ApplicationChannel.PLATFORM and body.status == ApplicationStatus.WITHDRAWN:
            for member_id in db.scalars(
                select(CompanyMembership.user_id).where(CompanyMembership.company_id == application.job.company_id)
            ):
                notify(
                    db,
                    member_id,
                    "application_withdrawn",
                    f"Sollicitatie ingetrokken voor ‘{application.job.title}’",
                    None,
                    f"/employer/applications/{application.id}",
                )
    db.commit()
    refreshed = _load(db, application.id)
    assert refreshed is not None
    return refreshed


def delete_mine(db: Session, user: User, application_id: uuid.UUID) -> None:
    application = get_mine(db, user, application_id)
    if application.channel == ApplicationChannel.PLATFORM and application.status not in (
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
    ):
        raise AppError("Trek de sollicitatie eerst in voordat je ze verwijdert.", code="withdraw_first", status_code=409)
    db.delete(application)
    db.commit()


# ── employer side ────────────────────────────────────────────────────────────


def _employer_scope(db: Session, user: User) -> list[uuid.UUID] | None:
    """Company ids the user may see applications for (None = all, for admins)."""
    return None if user.role == UserRole.ADMIN else member_company_ids(db, user)


def applicant_out(db: Session, application: Application, *, full: bool) -> ApplicantOut:
    candidate = application.user
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == candidate.id))
    out = ApplicantOut(
        id=application.id,
        job_id=application.job_id,
        job_title=application.job.title,
        company_id=application.job.company_id,
        candidate_name=candidate.full_name,
        candidate_email=candidate.email,
        candidate_city=profile.city if profile else None,
        candidate_headline=profile.headline if profile else None,
        status=application.status,
        applied_at=application.applied_at,
        has_cv=application.cv_version_id is not None,
        history=_history(application),
    )
    if full:
        out.cover_letter = application.cover_letter
        if application.cv_version and application.cv_version.content:
            out.cv = application.cv_version.content
        # Job-related qualifications only (skills), shown transparently; no ranking of candidates.
        if application.job.status == JobStatus.PUBLISHED:
            match = matching.get_or_compute(db, candidate, [application.job])[application.job.id]
            out.matching_skills = [s["name"] for s in match.result.get("matching_skills", [])]
            out.missing_required_skills = [s["name"] for s in match.result.get("missing_required_skills", [])]
    return out


def employer_list(db: Session, user: User, job_id: uuid.UUID | None, status: ApplicationStatus | None) -> list[ApplicantOut]:
    scope = _employer_scope(db, user)
    stmt = (
        select(Application.id)
        .join(Job, Job.id == Application.job_id)
        .where(Application.channel == ApplicationChannel.PLATFORM)
        .order_by(Application.applied_at.desc())
    )
    if scope is not None:
        stmt = stmt.where(Job.company_id.in_(scope))
    if job_id:
        stmt = stmt.where(Application.job_id == job_id)
    if status:
        stmt = stmt.where(Application.status == status)
    return [applicant_out(db, a, full=False) for a in (_load(db, i) for i in db.scalars(stmt.limit(500))) if a is not None]


def employer_get(db: Session, user: User, application_id: uuid.UUID) -> Application:
    application = _load(db, application_id)
    if application is None or application.channel != ApplicationChannel.PLATFORM:
        raise NotFoundError("Sollicitatie niet gevonden.")
    try:
        require_member(db, user, application.job.company_id)
    except PermissionDeniedError as exc:
        # Don't reveal that the application exists.
        raise NotFoundError("Sollicitatie niet gevonden.") from exc
    return application


def employer_update(db: Session, user: User, application_id: uuid.UUID, body: EmployerStatusUpdate) -> Application:
    application = employer_get(db, user, application_id)
    if application.status == ApplicationStatus.WITHDRAWN:
        raise AppError("De kandidaat heeft deze sollicitatie ingetrokken.", code="withdrawn", status_code=409)
    new = ApplicationStatus(body.status)
    _change_status(db, application, new, user, body.note)
    notify(
        db,
        application.user_id,
        "application_status",
        f"Update voor ‘{application.job.title}’",
        f"Nieuwe status: {STATUS_LABELS[new.value]}.",
        "/applications",
    )
    audit(
        db, "application.status_changed", actor_id=user.id, target_type="application", target_id=application.id, details={"to": new.value}
    )
    db.commit()
    refreshed = _load(db, application.id)
    assert refreshed is not None
    return refreshed
