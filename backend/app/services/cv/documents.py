"""Uploaded CV documents: validation, private storage, extraction and confirmation into the profile."""

import hashlib
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.db.base import utcnow
from app.integrations.ai.base import AIError
from app.integrations.ai.factory import llm_configured
from app.integrations.ai.prompts import CV_EXTRACTION
from app.integrations.storage.local import get_storage
from app.models.entities import BackgroundTask, CVDocument, CVVersion, User
from app.models.enums import CVVersionKind, CVVersionStatus, ExtractionStatus, TaskStatus
from app.schemas.cvs import ConfirmExtractionRequest, CVDocumentDetail, CVDocumentOut
from app.schemas.profile import ExtractedCV, ProfileContent
from app.services import ai_service, tasks
from app.services.audit import audit
from app.services.candidate_service import get_preferences, get_profile
from app.services.cv import rule_based
from app.services.cv.content import profile_to_cv_content
from app.services.cv.parsing import ExtractionError, detect_language, extract_text
from app.utils.files import detect_cv_type
from app.utils.text import content_hash

logger = logging.getLogger("talentflow.cv")


def upload(db: Session, user: User, filename: str, data: bytes) -> tuple[CVDocument, BackgroundTask | None]:
    settings = get_settings()
    if not data:
        raise AppError("Het bestand is leeg.", code="empty_file")
    if len(data) > settings.max_upload_bytes:
        raise AppError(f"Het bestand is groter dan {settings.max_upload_mb:g} MB.", code="file_too_large", status_code=413)
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    mime = detect_cv_type(data)
    if mime is None or extension not in ("pdf", "docx"):
        raise AppError(
            "Upload een PDF- of Word-bestand (.docx). Andere bestandstypes worden niet aanvaard.", code="unsupported_file", status_code=415
        )
    if (extension == "pdf") != (mime.endswith("pdf")):
        raise AppError("De bestandsextensie past niet bij de inhoud van het bestand.", code="unsupported_file", status_code=415)

    storage_key = get_storage().save(data)
    document = CVDocument(
        user_id=user.id,
        original_filename=filename[-255:],
        storage_key=storage_key,
        mime_type=mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        extraction_status=ExtractionStatus.PENDING,
    )
    db.add(document)
    db.flush()
    task = tasks.enqueue(
        db,
        "extract_cv",
        user_id=user.id,
        payload={"cv_id": str(document.id)},
        idempotency_key=f"extract_cv:{document.id}",
        timeout_seconds=int(settings.ai_timeout_seconds) + 60,
        commit=False,
    )
    audit(db, "cv.upload", actor_id=user.id, target_type="cv_document", target_id=document.id)
    db.commit()
    return document, task


def get_document(db: Session, user: User, cv_id: uuid.UUID) -> CVDocument:
    document = db.get(CVDocument, cv_id)
    if document is None or document.user_id != user.id:
        raise NotFoundError("Cv niet gevonden.")
    return document


def list_documents(db: Session, user: User) -> list[CVDocument]:
    return list(db.scalars(select(CVDocument).where(CVDocument.user_id == user.id).order_by(CVDocument.created_at.desc())))


def document_detail(db: Session, document: CVDocument) -> CVDocumentDetail:
    task = db.scalar(
        select(BackgroundTask)
        .where(BackgroundTask.type == "extract_cv", BackgroundTask.payload["cv_id"].astext == str(document.id))
        .order_by(BackgroundTask.created_at.desc())
    )
    return CVDocumentDetail(
        **CVDocumentOut.model_validate(document).model_dump(),
        extracted=ExtractedCV.model_validate(document.extracted_data) if document.extracted_data else None,
        task_id=task.id if task and task.status in (TaskStatus.QUEUED, TaskStatus.RUNNING) else None,
    )


def delete_document(db: Session, user: User, cv_id: uuid.UUID) -> None:
    document = get_document(db, user, cv_id)
    key = document.storage_key
    db.delete(document)
    audit(db, "cv.delete", actor_id=user.id, target_type="cv_document", target_id=cv_id)
    db.commit()
    get_storage().delete(key)


def read_file(document: CVDocument) -> bytes:
    if not document.storage_key:
        raise NotFoundError("Het originele bestand is niet meer beschikbaar.")
    return get_storage().read(document.storage_key)


# ── extraction (runs in the worker) ─────────────────────────────────────────


def _ai_extract(db: Session, user_id: uuid.UUID, text: str) -> ExtractedCV:
    result, _, _ = ai_service.generate(
        db,
        user_id=user_id,
        operation="cv_extraction",
        system=CV_EXTRACTION,
        user=f"<document>\n{text[:20000]}\n</document>",
        schema=ExtractedCV,
        temperature=0.0,
    )
    # Fresh ids: never trust identifiers produced by the model.
    data = result.model_dump(mode="json")
    for section in ("experiences", "education", "certifications", "projects"):
        for item in data["profile"][section]:
            item.pop("id", None)
    return ExtractedCV.model_validate(data)


def run_extraction(db: Session, cv_id: uuid.UUID, progress) -> None:
    document = db.get(CVDocument, cv_id)
    if document is None:
        return
    document.extraction_status = ExtractionStatus.PROCESSING
    db.commit()
    try:
        progress(15, "Tekst uit het document halen")
        text, needs_ocr = extract_text(read_file(document), document.mime_type)
    except ExtractionError as exc:
        document.extraction_status = ExtractionStatus.FAILED
        document.extraction_error = exc.message
        db.commit()
        return
    document.extracted_text = text
    document.language = detect_language(text)
    if needs_ocr:
        document.extraction_status = ExtractionStatus.NEEDS_OCR
        document.extraction_error = (
            "Dit lijkt een gescande PDF (afbeeldingen zonder tekst). Upload een PDF met selecteerbare tekst of een Word-bestand, "
            "of vul je profiel handmatig in."
        )
        db.commit()
        return
    db.commit()

    if llm_configured():
        progress(40, "Gegevens herkennen met AI")
        try:
            extracted = _ai_extract(db, document.user_id, text)
            method = "ai"
        except AIError as exc:
            logger.warning("AI extraction failed (%s); using rule-based extraction", exc.code)
            extracted, method = rule_based.extract(text, document.language), "rule_based"
            document.extraction_error = exc.user_message + " We gebruikten daarom een basisextractie."
    else:
        extracted, method = rule_based.extract(text, document.language), "rule_based"
    extracted.language = extracted.language or document.language
    document.extracted_data = extracted.model_dump(mode="json")
    document.extraction_method = method
    document.extraction_status = ExtractionStatus.COMPLETED
    db.commit()
    progress(100, "Klaar")


def confirm(db: Session, user: User, cv_id: uuid.UUID, body: ConfirmExtractionRequest) -> CVVersion:
    """Copies the reviewed data into the candidate's profile and stores an immutable 'original' CV version."""
    document = get_document(db, user, cv_id)
    profile = get_profile(db, user.id)
    contact = body.contact
    profile.headline = body.headline
    profile.summary = body.summary
    profile.phone = contact.phone or profile.phone
    profile.city = contact.city or profile.city
    profile.linkedin_url = contact.linkedin_url or profile.linkedin_url
    profile.website_url = contact.website_url or profile.website_url
    profile.content = ProfileContent.model_validate(body.profile.model_dump()).model_dump(mode="json")
    profile.content_hash = content_hash([profile.headline, profile.summary, profile.city, profile.content])
    profile.confirmed_at = utcnow()
    if contact.full_name and contact.full_name.strip() and len(contact.full_name) >= 2:
        user.full_name = contact.full_name.strip()
    document.confirmed_at = utcnow()
    db.flush()
    version = CVVersion(
        user_id=user.id,
        source_cv_id=document.id,
        kind=CVVersionKind.ORIGINAL,
        status=CVVersionStatus.READY,
        title=f"Origineel: {document.original_filename}"[:200],
        language=document.language or "nl",
        template="modern",
        content=profile_to_cv_content(user, profile).model_dump(mode="json"),
        is_simulated=False,
    )
    version.generated_content = version.content
    db.add(version)
    tasks.enqueue(
        db,
        "embed_profile",
        user_id=user.id,
        payload={"user_id": str(user.id)},
        idempotency_key=f"embed_profile:{user.id}",
        max_attempts=3,
        timeout_seconds=120,
        commit=False,
    )
    audit(db, "cv.confirm", actor_id=user.id, target_type="cv_document", target_id=document.id)
    get_preferences(db, user.id)
    db.commit()
    return version
