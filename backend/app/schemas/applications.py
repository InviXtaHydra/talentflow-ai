import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.enums import ApplicationChannel, ApplicationStatus
from app.schemas.common import LongText
from app.schemas.jobs import JobSummaryOut

CANDIDATE_TRACKING_STATUSES = {
    ApplicationStatus.SAVED,
    ApplicationStatus.READY_TO_APPLY,
    ApplicationStatus.APPLIED,
    ApplicationStatus.IN_REVIEW,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.OFFER,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
}
EMPLOYER_STATUSES = {ApplicationStatus.IN_REVIEW, ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER, ApplicationStatus.REJECTED}


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    channel: ApplicationChannel
    # External tracking can start at any of the early stages; platform applications are always "applied".
    status: Literal["saved", "ready_to_apply", "applied"] = "saved"
    cv_version_id: uuid.UUID | None = None
    cover_letter: LongText | None = None
    notes: LongText | None = None
    # Explicit consent to share the selected CV and profile details with this employer.
    share_consent: bool = False


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: LongText | None = None
    note: str | None = Field(default=None, max_length=500)


class EmployerStatusUpdate(BaseModel):
    status: Literal["in_review", "interview", "offer", "rejected"]
    note: str | None = Field(default=None, max_length=500)


class StatusHistoryOut(BaseModel):
    from_status: str | None
    to_status: str
    changed_by_role: str | None
    note: str | None
    created_at: datetime


class ApplicationOut(BaseModel):
    id: uuid.UUID
    job: JobSummaryOut
    status: ApplicationStatus
    channel: ApplicationChannel
    cv_version_id: uuid.UUID | None
    cv_version_title: str | None
    notes: str | None
    cover_letter: str | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
    history: list[StatusHistoryOut] = []


class ApplicantOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    company_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    candidate_city: str | None
    candidate_headline: str | None
    status: ApplicationStatus
    applied_at: datetime | None
    cover_letter: str | None = None
    has_cv: bool
    matching_skills: list[str] = []
    missing_required_skills: list[str] = []
    history: list[StatusHistoryOut] = []
    cv: dict[str, Any] | None = None
