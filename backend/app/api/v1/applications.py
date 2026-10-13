import uuid

from fastapi import APIRouter, Response

from app.api.deps import CandidateUser, DbSession, EmployerUser
from app.core.errors import NotFoundError
from app.models.enums import ApplicationStatus
from app.schemas.applications import (
    ApplicantOut,
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    EmployerStatusUpdate,
)
from app.schemas.common import Message
from app.services import application_service, dashboard_service
from app.services.documents.export import export_version

router = APIRouter(tags=["applications"])


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def create(body: ApplicationCreate, db: DbSession, user: CandidateUser) -> ApplicationOut:
    return application_service.application_out(application_service.create(db, user, body))


@router.get("/applications/me", response_model=list[ApplicationOut])
def mine(db: DbSession, user: CandidateUser) -> list[ApplicationOut]:
    return [application_service.application_out(a) for a in application_service.list_mine(db, user)]


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_one(application_id: uuid.UUID, db: DbSession, user: CandidateUser) -> ApplicationOut:
    return application_service.application_out(application_service.get_mine(db, user, application_id))


@router.patch("/applications/{application_id}", response_model=ApplicationOut)
def update(application_id: uuid.UUID, body: ApplicationUpdate, db: DbSession, user: CandidateUser) -> ApplicationOut:
    return application_service.application_out(application_service.update_mine(db, user, application_id, body))


@router.delete("/applications/{application_id}", response_model=Message)
def delete(application_id: uuid.UUID, db: DbSession, user: CandidateUser) -> Message:
    application_service.delete_mine(db, user, application_id)
    return Message(message="Verwijderd uit je overzicht.")


# ── employer ─────────────────────────────────────────────────────────────────


@router.get("/employer/dashboard", tags=["employer"])
def employer_dashboard(db: DbSession, user: EmployerUser) -> dict:
    return dashboard_service.employer_dashboard(db, user)


@router.get("/employer/applications", response_model=list[ApplicantOut], tags=["employer"])
def employer_applications(
    db: DbSession, user: EmployerUser, job_id: uuid.UUID | None = None, status: ApplicationStatus | None = None
) -> list[ApplicantOut]:
    return application_service.employer_list(db, user, job_id, status)


@router.get("/employer/applications/{application_id}", response_model=ApplicantOut, tags=["employer"])
def employer_application(application_id: uuid.UUID, db: DbSession, user: EmployerUser) -> ApplicantOut:
    return application_service.applicant_out(db, application_service.employer_get(db, user, application_id), full=True)


@router.patch("/employer/applications/{application_id}", response_model=ApplicantOut, tags=["employer"])
def employer_update(application_id: uuid.UUID, body: EmployerStatusUpdate, db: DbSession, user: EmployerUser) -> ApplicantOut:
    return application_service.applicant_out(db, application_service.employer_update(db, user, application_id, body), full=True)


@router.get("/employer/applications/{application_id}/cv", tags=["employer"], summary="The CV the candidate chose to share (PDF)")
def employer_cv(application_id: uuid.UUID, db: DbSession, user: EmployerUser) -> Response:
    application = application_service.employer_get(db, user, application_id)
    if application.cv_version is None or application.shared_with_employer_at is None:
        raise NotFoundError("Er is geen cv gedeeld bij deze sollicitatie.")
    data, mime, filename = export_version(db, application.cv_version, "pdf", None, preview=True)
    return Response(data, media_type=mime, headers={"Content-Disposition": f'inline; filename="{filename}"', "Cache-Control": "no-store"})
