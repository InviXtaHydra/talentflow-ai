import uuid
from urllib.parse import quote

from fastapi import APIRouter, File, Response, UploadFile
from sqlalchemy import select

from app.api.deps import CandidateUser, DbSession
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.models.entities import CVAnalysis
from app.schemas.common import Message, TaskRef
from app.schemas.cvs import (
    ConfirmExtractionRequest,
    CVAnalysisOut,
    CVDocumentDetail,
    CVDocumentOut,
    CVVersionDetail,
    CVVersionSummary,
    CVVersionUpdate,
    ExportRequest,
    ManualVersionRequest,
    OptimizeRequest,
    OptimizeStarted,
    RestoreRequest,
    UploadResult,
)
from app.services import tasks
from app.services.cv import documents, optimizer, versions
from app.services.documents.export import export_version

router = APIRouter(tags=["cvs"])


def _download(data: bytes, mime: str, filename: str, inline: bool) -> Response:
    disposition = "inline" if inline else "attachment"
    return Response(
        data,
        media_type=mime,
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ── uploaded CV documents ───────────────────────────────────────────────────


@router.post("/cvs/upload", response_model=UploadResult, status_code=201)
async def upload(db: DbSession, user: CandidateUser, file: UploadFile = File(...)) -> UploadResult:
    limit = get_settings().max_upload_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError(f"Het bestand is groter dan {get_settings().max_upload_mb:g} MB.", code="file_too_large", status_code=413)
    document, task = documents.upload(db, user, file.filename or "cv", data)
    return UploadResult(document=CVDocumentOut.model_validate(document), task_id=task.id if task else None)


@router.get("/cvs", response_model=list[CVDocumentOut])
def list_cvs(db: DbSession, user: CandidateUser) -> list[CVDocumentOut]:
    return [CVDocumentOut.model_validate(d) for d in documents.list_documents(db, user)]


@router.get("/cvs/{cv_id}", response_model=CVDocumentDetail)
def get_cv(cv_id: uuid.UUID, db: DbSession, user: CandidateUser) -> CVDocumentDetail:
    return documents.document_detail(db, documents.get_document(db, user, cv_id))


@router.get("/cvs/{cv_id}/file", summary="Download the original uploaded file")
def download_original(cv_id: uuid.UUID, db: DbSession, user: CandidateUser) -> Response:
    document = documents.get_document(db, user, cv_id)
    extension = "pdf" if document.mime_type.endswith("pdf") else "docx"
    return _download(documents.read_file(document), document.mime_type, f"origineel-cv.{extension}", inline=extension == "pdf")


@router.post("/cvs/{cv_id}/confirm", response_model=CVVersionSummary, summary="Save the reviewed extraction to the profile")
def confirm(cv_id: uuid.UUID, body: ConfirmExtractionRequest, db: DbSession, user: CandidateUser) -> CVVersionSummary:
    return versions.summary(documents.confirm(db, user, cv_id, body))


@router.post("/cvs/{cv_id}/retry-extraction", response_model=TaskRef)
def retry_extraction(cv_id: uuid.UUID, db: DbSession, user: CandidateUser) -> TaskRef:
    document = documents.get_document(db, user, cv_id)
    task = tasks.enqueue(
        db,
        "extract_cv",
        user_id=user.id,
        payload={"cv_id": str(document.id)},
        idempotency_key=f"extract_cv:{document.id}",
        timeout_seconds=int(get_settings().ai_timeout_seconds) + 60,
    )
    return TaskRef(task_id=str(task.id), status=task.status.value)


@router.delete("/cvs/{cv_id}", response_model=Message)
def delete_cv(cv_id: uuid.UUID, db: DbSession, user: CandidateUser) -> Message:
    documents.delete_document(db, user, cv_id)
    return Message(message="Het cv-bestand en de herkende gegevens zijn verwijderd.")


@router.post("/cvs/{cv_id}/analyze", response_model=TaskRef)
def analyze(cv_id: uuid.UUID, db: DbSession, user: CandidateUser) -> TaskRef:
    documents.get_document(db, user, cv_id)
    task = tasks.enqueue(
        db,
        "analyze_cv",
        user_id=user.id,
        payload={"cv_id": str(cv_id)},
        idempotency_key=f"analyze:{user.id}:{cv_id}",
        timeout_seconds=int(get_settings().ai_timeout_seconds) + 60,
    )
    return TaskRef(task_id=str(task.id), status=task.status.value)


@router.post("/cv-analyses", response_model=TaskRef, summary="Analyse the confirmed profile (no uploaded CV needed)")
def analyze_profile(db: DbSession, user: CandidateUser) -> TaskRef:
    task = tasks.enqueue(
        db,
        "analyze_cv",
        user_id=user.id,
        payload={"cv_id": None},
        idempotency_key=f"analyze:{user.id}:profile",
        timeout_seconds=int(get_settings().ai_timeout_seconds) + 60,
    )
    return TaskRef(task_id=str(task.id), status=task.status.value)


@router.get("/cv-analyses", response_model=list[CVAnalysisOut])
def list_analyses(db: DbSession, user: CandidateUser) -> list[CVAnalysisOut]:
    rows = db.scalars(select(CVAnalysis).where(CVAnalysis.user_id == user.id).order_by(CVAnalysis.created_at.desc()).limit(20))
    return [CVAnalysisOut.model_validate(a) for a in rows]


@router.get("/cvs/{cv_id}/versions", response_model=list[CVVersionSummary])
def cv_versions(cv_id: uuid.UUID, db: DbSession, user: CandidateUser) -> list[CVVersionSummary]:
    documents.get_document(db, user, cv_id)
    return versions.list_versions(db, user, cv_id)


# ── CV versions ──────────────────────────────────────────────────────────────


@router.get("/cv-versions", response_model=list[CVVersionSummary])
def list_versions(db: DbSession, user: CandidateUser) -> list[CVVersionSummary]:
    return versions.list_versions(db, user)


@router.post("/cv-versions", response_model=CVVersionSummary, status_code=201, summary="Create an editable CV from the profile")
def create_version(body: ManualVersionRequest, db: DbSession, user: CandidateUser) -> CVVersionSummary:
    return versions.summary(versions.create_from_profile(db, user, body))


@router.get("/cv-versions/{version_id}", response_model=CVVersionDetail)
def get_version(version_id: uuid.UUID, db: DbSession, user: CandidateUser) -> CVVersionDetail:
    return versions.detail(db, user, versions.get_version(db, user, version_id))


@router.patch("/cv-versions/{version_id}", response_model=CVVersionDetail)
def update_version(version_id: uuid.UUID, body: CVVersionUpdate, db: DbSession, user: CandidateUser) -> CVVersionDetail:
    return versions.detail(db, user, versions.update_version(db, user, version_id, body))


@router.post("/cv-versions/{version_id}/duplicate", response_model=CVVersionSummary, status_code=201)
def duplicate(version_id: uuid.UUID, db: DbSession, user: CandidateUser) -> CVVersionSummary:
    return versions.summary(versions.duplicate(db, user, version_id))


@router.delete("/cv-versions/{version_id}", response_model=Message)
def delete_version(version_id: uuid.UUID, db: DbSession, user: CandidateUser) -> Message:
    versions.delete_version(db, user, version_id)
    return Message(message="De cv-versie is verwijderd.")


@router.post("/cv-versions/{version_id}/export", summary="Download as PDF or DOCX")
def export(version_id: uuid.UUID, body: ExportRequest, db: DbSession, user: CandidateUser) -> Response:
    version = versions.get_version(db, user, version_id)
    data, mime, filename = export_version(db, version, body.format, body.template, preview=body.preview)
    return _download(data, mime, filename, inline=body.preview)


# ── vacancy-specific optimization ───────────────────────────────────────────


@router.post("/jobs/{job_id}/optimize-cv", response_model=OptimizeStarted, status_code=202)
def optimize(job_id: uuid.UUID, body: OptimizeRequest, db: DbSession, user: CandidateUser) -> OptimizeStarted:
    version, task = optimizer.start(
        db, user, job_id, source_version_id=body.source_version_id, language=body.language, template=body.template
    )
    return OptimizeStarted(optimization_id=version.id, task_id=task.id if task else None, status=version.status.value)


def _optimization(db, user, optimization_id: uuid.UUID):
    version = versions.get_version(db, user, optimization_id)
    if version.kind.value != "optimized":
        raise NotFoundError("Optimalisatie niet gevonden.")
    return version


@router.get("/cv-optimizations/{optimization_id}", response_model=CVVersionDetail)
def get_optimization(optimization_id: uuid.UUID, db: DbSession, user: CandidateUser) -> CVVersionDetail:
    return versions.detail(db, user, _optimization(db, user, optimization_id))


@router.patch("/cv-optimizations/{optimization_id}", response_model=CVVersionDetail)
def update_optimization(optimization_id: uuid.UUID, body: CVVersionUpdate, db: DbSession, user: CandidateUser) -> CVVersionDetail:
    _optimization(db, user, optimization_id)
    return versions.detail(db, user, versions.update_version(db, user, optimization_id, body))


@router.post("/cv-optimizations/{optimization_id}/restore", response_model=CVVersionDetail)
def restore(optimization_id: uuid.UUID, body: RestoreRequest, db: DbSession, user: CandidateUser) -> CVVersionDetail:
    _optimization(db, user, optimization_id)
    return versions.detail(db, user, versions.restore(db, user, optimization_id, body.target))


@router.post("/cv-optimizations/{optimization_id}/regenerate", response_model=OptimizeStarted, status_code=202)
def regenerate(optimization_id: uuid.UUID, db: DbSession, user: CandidateUser) -> OptimizeStarted:
    version, task = optimizer.regenerate(db, user, optimization_id)
    return OptimizeStarted(optimization_id=version.id, task_id=task.id if task else None, status=version.status.value)


@router.post("/cv-optimizations/{optimization_id}/export")
def export_optimization(optimization_id: uuid.UUID, body: ExportRequest, db: DbSession, user: CandidateUser) -> Response:
    version = _optimization(db, user, optimization_id)
    data, mime, filename = export_version(db, version, body.format, body.template, preview=body.preview)
    return _download(data, mime, filename, inline=body.preview)
