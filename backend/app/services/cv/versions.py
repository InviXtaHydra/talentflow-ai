import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, NotFoundError
from app.db.base import utcnow
from app.models.entities import CVVersion, Job, User
from app.models.enums import CVVersionKind, CVVersionStatus, TaskStatus
from app.schemas.cv import CVContent
from app.schemas.cvs import CVVersionDetail, CVVersionSummary, CVVersionUpdate, ManualVersionRequest
from app.services.audit import audit
from app.services.candidate_service import get_profile
from app.services.cv.content import profile_to_cv_content
from app.services.cv.optimizer import active_task


def get_version(db: Session, user: User, version_id: uuid.UUID) -> CVVersion:
    version = db.scalar(
        select(CVVersion).where(CVVersion.id == version_id).options(selectinload(CVVersion.target_job).selectinload(Job.company))
    )
    if version is None or version.user_id != user.id:
        raise NotFoundError("Cv-versie niet gevonden.")
    return version


def summary(version: CVVersion) -> CVVersionSummary:
    job = version.target_job
    return CVVersionSummary(
        id=version.id,
        kind=version.kind,
        status=version.status,
        title=version.title,
        language=version.language,
        template=version.template,
        source_cv_id=version.source_cv_id,
        target_job_id=version.target_job_id,
        target_job_title=job.title if job else None,
        target_company_name=job.company.name if job else None,
        score_before=(version.match_before or {}).get("score"),
        score_after=(version.match_after or {}).get("score"),
        is_simulated=version.is_simulated,
        created_at=version.created_at,
        updated_at=version.updated_at,
        user_edited_at=version.user_edited_at,
        last_exported_at=version.last_exported_at,
    )


def detail(db: Session, user: User, version: CVVersion) -> CVVersionDetail:
    task = active_task(db, version) if version.kind == CVVersionKind.OPTIMIZED else None
    original = None
    if version.source_snapshot:
        original = CVContent.model_validate(version.source_snapshot)
    return CVVersionDetail(
        **summary(version).model_dump(),
        content=CVContent.model_validate(version.content) if version.content else None,
        generated_content=CVContent.model_validate(version.generated_content) if version.generated_content else None,
        original_content=original,
        optimization=version.optimization,
        match_before=version.match_before,
        match_after=version.match_after,
        provider=version.provider,
        model=version.model,
        error_message=version.error_message or (task.error_message if task and task.status == TaskStatus.FAILED else None),
        task_id=task.id if task else None,
        task_status=task.status.value if task else None,
        task_progress=task.progress if task else None,
        task_message=task.progress_message if task else None,
    )


def list_versions(db: Session, user: User, source_cv_id: uuid.UUID | None = None) -> list[CVVersionSummary]:
    stmt = (
        select(CVVersion)
        .where(CVVersion.user_id == user.id)
        .options(selectinload(CVVersion.target_job).selectinload(Job.company))
        .order_by(CVVersion.created_at.desc())
    )
    if source_cv_id:
        stmt = stmt.where(CVVersion.source_cv_id == source_cv_id)
    return [summary(v) for v in db.scalars(stmt)]


def update_version(db: Session, user: User, version_id: uuid.UUID, body: CVVersionUpdate) -> CVVersion:
    version = get_version(db, user, version_id)
    if version.status != CVVersionStatus.READY:
        raise AppError("Deze versie wordt nog gegenereerd.", code="not_ready", status_code=409)
    if version.kind == CVVersionKind.ORIGINAL and body.content is not None:
        raise AppError(
            "Het originele cv blijft ongewijzigd. Maak een kopie om het te bewerken.", code="original_immutable", status_code=409
        )
    if body.title is not None:
        version.title = body.title
    if body.template is not None:
        version.template = body.template
    if body.content is not None:
        version.content = body.content.model_dump(mode="json")
        version.user_edited_at = utcnow()
    db.commit()
    return version


def restore(db: Session, user: User, version_id: uuid.UUID, target: str) -> CVVersion:
    version = get_version(db, user, version_id)
    if version.kind == CVVersionKind.ORIGINAL:
        raise AppError("Het originele cv is nooit gewijzigd.", code="original_immutable", status_code=409)
    if target == "generated":
        if not version.generated_content:
            raise AppError("Er is geen gegenereerde versie om naar terug te gaan.", code="nothing_to_restore", status_code=409)
        version.content = version.generated_content
    else:
        if not version.source_snapshot:
            raise AppError("Er is geen originele inhoud bewaard voor deze versie.", code="nothing_to_restore", status_code=409)
        version.content = version.source_snapshot
    version.user_edited_at = utcnow()
    db.commit()
    return version


def duplicate(db: Session, user: User, version_id: uuid.UUID) -> CVVersion:
    version = get_version(db, user, version_id)
    if not version.content:
        raise AppError("Deze versie heeft (nog) geen inhoud.", code="not_ready", status_code=409)
    copy = CVVersion(
        user_id=user.id,
        source_cv_id=version.source_cv_id,
        target_job_id=version.target_job_id,
        kind=CVVersionKind.MANUAL,
        status=CVVersionStatus.READY,
        title=f"Kopie van {version.title}"[:200],
        language=version.language,
        template=version.template,
        content=version.content,
        generated_content=version.content,
        source_snapshot=version.source_snapshot or version.content,
    )
    db.add(copy)
    db.commit()
    return copy


def create_from_profile(db: Session, user: User, body: ManualVersionRequest) -> CVVersion:
    profile = get_profile(db, user.id)
    content = profile_to_cv_content(user, profile).model_dump(mode="json")
    version = CVVersion(
        user_id=user.id,
        kind=CVVersionKind.MANUAL,
        status=CVVersionStatus.READY,
        title=body.title,
        language=body.language,
        template=body.template,
        content=content,
        generated_content=content,
        source_snapshot=content,
    )
    db.add(version)
    db.commit()
    return version


def delete_version(db: Session, user: User, version_id: uuid.UUID) -> None:
    version = get_version(db, user, version_id)
    if version.status == CVVersionStatus.GENERATING:
        raise AppError("Wacht tot de versie klaar is voordat je ze verwijdert.", code="not_ready", status_code=409)
    db.delete(version)
    audit(db, "cv_version.delete", actor_id=user.id, target_type="cv_version", target_id=version_id)
    db.commit()
