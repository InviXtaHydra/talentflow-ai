import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.enums import CVVersionKind, CVVersionStatus, ExtractionStatus
from app.schemas.common import ApiModel, LongText, ShortText
from app.schemas.cv import CVContent
from app.schemas.profile import ContactDetails, ExtractedCV, ProfileContent


class CVDocumentOut(ApiModel):
    id: uuid.UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    language: str | None
    extraction_status: ExtractionStatus
    extraction_method: str | None
    extraction_error: str | None
    confirmed_at: datetime | None
    created_at: datetime
    is_demo: bool


class CVDocumentDetail(CVDocumentOut):
    extracted: ExtractedCV | None = None
    task_id: uuid.UUID | None = None


class UploadResult(BaseModel):
    document: CVDocumentOut
    task_id: uuid.UUID | None


class ConfirmExtractionRequest(BaseModel):
    """The candidate's reviewed and corrected version of the extracted data."""

    contact: ContactDetails = Field(default_factory=ContactDetails)
    headline: ShortText | None = None
    summary: LongText | None = None
    profile: ProfileContent


class AnalysisCheck(BaseModel):
    key: str
    passed: bool
    weight: int
    detail: dict[str, Any] = Field(default_factory=dict)


class CVAnalysisOut(ApiModel):
    id: uuid.UUID
    cv_document_id: uuid.UUID | None
    status: str
    method: str
    quality_score: int | None
    checks: list[AnalysisCheck]
    strengths: list[str]
    suggestions: list[str]
    provider: str | None
    model: str | None
    created_at: datetime


class CVVersionSummary(ApiModel):
    id: uuid.UUID
    kind: CVVersionKind
    status: CVVersionStatus
    title: str
    language: str
    template: str
    source_cv_id: uuid.UUID | None
    target_job_id: uuid.UUID | None
    target_job_title: str | None = None
    target_company_name: str | None = None
    score_before: int | None = None
    score_after: int | None = None
    is_simulated: bool
    created_at: datetime
    updated_at: datetime
    user_edited_at: datetime | None
    last_exported_at: datetime | None


class CVVersionDetail(CVVersionSummary):
    content: CVContent | None
    generated_content: CVContent | None
    original_content: CVContent | None = None
    optimization: dict[str, Any] | None
    match_before: dict[str, Any] | None
    match_after: dict[str, Any] | None
    provider: str | None
    model: str | None
    error_message: str | None
    task_id: uuid.UUID | None = None
    task_status: str | None = None
    task_progress: int | None = None
    task_message: str | None = None


class CVVersionUpdate(BaseModel):
    title: ShortText | None = None
    content: CVContent | None = None
    template: Literal["modern", "minimal", "technical"] | None = None


class OptimizeRequest(BaseModel):
    source_version_id: uuid.UUID | None = None
    language: Literal["nl", "fr", "en"] | None = None
    template: Literal["modern", "minimal", "technical"] = "modern"


class OptimizeStarted(BaseModel):
    optimization_id: uuid.UUID
    task_id: uuid.UUID | None
    status: str


class ExportRequest(BaseModel):
    format: Literal["pdf", "docx"] = "pdf"
    template: Literal["modern", "minimal", "technical"] | None = None
    preview: bool = False


class RestoreRequest(BaseModel):
    target: Literal["generated", "original"]


class ManualVersionRequest(BaseModel):
    title: ShortText = "Mijn cv"
    template: Literal["modern", "minimal", "technical"] = "modern"
    language: Literal["nl", "fr", "en"] = "nl"
