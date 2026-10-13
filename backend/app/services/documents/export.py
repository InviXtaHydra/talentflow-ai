from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.base import utcnow
from app.models.entities import CVVersion
from app.models.enums import CVVersionStatus
from app.schemas.cv import CVContent
from app.services.documents.docx_export import render_docx
from app.services.documents.pdf import render_pdf
from app.utils.files import DOCX_MIME, PDF_MIME, safe_filename


def export_version(db: Session, version: CVVersion, fmt: str, template: str | None, *, preview: bool) -> tuple[bytes, str, str]:
    """Renders the version's current (edited) content. Returns (bytes, mime type, download filename)."""
    if version.status != CVVersionStatus.READY or not version.content:
        raise AppError("Deze versie is nog niet klaar om te exporteren.", code="not_ready", status_code=409)
    cv = CVContent.model_validate(version.content)
    template = template or version.template
    title = f"CV {cv.contact.full_name or ''}".strip()
    if fmt == "pdf":
        data, mime = render_pdf(cv, template=template, language=version.language, title=title), PDF_MIME
    else:
        data, mime = render_docx(cv, template=template, language=version.language, title=title), DOCX_MIME
    job_part = version.target_job.title if version.target_job else ""
    filename = safe_filename("CV", cv.contact.full_name or "", job_part, extension=fmt)
    if not preview:
        version.export_count += 1
        version.last_exported_at = utcnow()
        version.last_export_format = fmt
        db.commit()
    return data, mime, filename
