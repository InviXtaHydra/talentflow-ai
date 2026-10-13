"""All database tables. One module keeps the relationships between them easy to follow."""

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin, utcnow
from app.models.enums import (
    ApplicationChannel,
    ApplicationStatus,
    CompanyRole,
    CVVersionKind,
    CVVersionStatus,
    EducationLevel,
    EmploymentType,
    ExperienceLevel,
    ExtractionStatus,
    JobSource,
    JobStatus,
    RemotePolicy,
    RemotePreference,
    SalaryPeriod,
    TaskStatus,
    TokenPurpose,
    UserRole,
)

EMBEDDING_DIMENSIONS = 768


def enum_type(enum_cls: type[StrEnum], name: str | None = None) -> Enum:
    # Stored as VARCHAR + CHECK constraint (not a native PG enum): adding a value later is a simple migration.
    return Enum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
        create_constraint=True,
        # The name becomes the CHECK constraint's name; tables with two columns of one enum pass their own.
        name=name or enum_cls.__name__.lower(),
    )


def fk(target: str, ondelete: str = "CASCADE") -> ForeignKey:
    return ForeignKey(target, ondelete=ondelete)


# ── Users and authentication ────────────────────────────────────────────────


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(enum_type(UserRole), index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    locale: Mapped[str] = mapped_column(String(8), default="nl")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_processing_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    candidate_profile: Mapped["CandidateProfile | None"] = relationship(back_populates="user", passive_deletes=True)
    preferences: Mapped["CandidatePreference | None"] = relationship(back_populates="user", passive_deletes=True)
    memberships: Mapped[list["CompanyMembership"]] = relationship(back_populates="user", passive_deletes=True)


class UserSession(IdMixin, Base):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    user_agent: Mapped[str | None] = mapped_column(String(300))

    user: Mapped[User] = relationship(back_populates="sessions")


class AuthToken(IdMixin, Base):
    """Single-use tokens for e-mail verification and password reset (stored as a keyed hash)."""

    __tablename__ = "auth_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    purpose: Mapped[TokenPurpose] = mapped_column(enum_type(TokenPurpose))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ── Candidates ───────────────────────────────────────────────────────────────


class CandidateProfile(IdMixin, TimestampMixin, Base):
    """The candidate's *confirmed* professional profile.

    `content` follows `app.schemas.profile.ProfileContent` (experiences, education, skills, ...).
    Data extracted from an uploaded CV lives on `CVDocument.extracted_data` until the candidate confirms it."""

    __tablename__ = "candidate_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), unique=True)
    headline: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(50))
    city: Mapped[str | None] = mapped_column(String(120))
    linkedin_url: Mapped[str | None] = mapped_column(String(300))
    website_url: Mapped[str | None] = mapped_column(String(300))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    embedding_hash: Mapped[str | None] = mapped_column(String(64))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="candidate_profile")


class CandidatePreference(IdMixin, TimestampMixin, Base):
    __tablename__ = "candidate_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), unique=True)
    desired_titles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    preferred_locations: Mapped[list[str]] = mapped_column(JSONB, default=list)
    max_commute_km: Mapped[int | None] = mapped_column(Integer)
    remote_preference: Mapped[RemotePreference] = mapped_column(enum_type(RemotePreference), default=RemotePreference.ANY)
    employment_types: Mapped[list[str]] = mapped_column(JSONB, default=list)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    salary_period: Mapped[SalaryPeriod] = mapped_column(enum_type(SalaryPeriod), default=SalaryPeriod.MONTH)
    industries: Mapped[list[str]] = mapped_column(JSONB, default=list)
    languages: Mapped[list[str]] = mapped_column(JSONB, default=list)
    available_from: Mapped[date | None] = mapped_column(Date)
    availability_note: Mapped[str | None] = mapped_column(String(200))

    user: Mapped[User] = relationship(back_populates="preferences")


# ── Companies and jobs ──────────────────────────────────────────────────────


class Company(IdMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    website_url: Mapped[str | None] = mapped_column(String(300))
    industry: Mapped[str | None] = mapped_column(String(120), index=True)
    city: Mapped[str | None] = mapped_column(String(120))
    size: Mapped[str | None] = mapped_column(String(40))
    logo_storage_key: Mapped[str | None] = mapped_column(String(80))
    logo_mime_type: Mapped[str | None] = mapped_column(String(40))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    memberships: Mapped[list["CompanyMembership"]] = relationship(
        back_populates="company", cascade="all, delete-orphan", passive_deletes=True
    )
    jobs: Mapped[list["Job"]] = relationship(back_populates="company", passive_deletes=True)


class CompanyMembership(IdMixin, Base):
    __tablename__ = "company_memberships"
    __table_args__ = (UniqueConstraint("company_id", "user_id", name="uq_company_memberships_company_user"),)

    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("companies.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    role: Mapped[CompanyRole] = mapped_column(enum_type(CompanyRole), default=CompanyRole.RECRUITER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped[Company] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Job(IdMixin, TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
        CheckConstraint("salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max", name="salary_range"),
        Index("ix_jobs_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_jobs_status_published_at", "status", "published_at"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("companies.id"), index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, fk("users.id", "SET NULL"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    responsibilities: Mapped[list[str]] = mapped_column(JSONB, default=list)
    qualifications: Mapped[list[str]] = mapped_column(JSONB, default=list)
    min_years_experience: Mapped[int | None] = mapped_column(Integer)
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(enum_type(ExperienceLevel))
    education_level: Mapped[EducationLevel | None] = mapped_column(enum_type(EducationLevel))
    required_languages: Mapped[list[str]] = mapped_column(JSONB, default=list)
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    remote_policy: Mapped[RemotePolicy] = mapped_column(enum_type(RemotePolicy), default=RemotePolicy.ONSITE)
    employment_type: Mapped[EmploymentType] = mapped_column(enum_type(EmploymentType), default=EmploymentType.FULL_TIME)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    salary_period: Mapped[SalaryPeriod | None] = mapped_column(enum_type(SalaryPeriod))
    # Salary normalized to EUR per year, for filtering and sorting across periods.
    salary_annual_min_eur: Mapped[int | None] = mapped_column(Integer, index=True)
    salary_annual_max_eur: Mapped[int | None] = mapped_column(Integer)
    industry: Mapped[str | None] = mapped_column(String(120), index=True)
    language: Mapped[str] = mapped_column(String(2), default="nl")
    application_deadline: Mapped[date | None] = mapped_column(Date)
    application_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[JobStatus] = mapped_column(enum_type(JobStatus), default=JobStatus.DRAFT)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[JobSource] = mapped_column(enum_type(JobSource), default=JobSource.EMPLOYER)
    external_id: Mapped[str | None] = mapped_column(String(200))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    embedding_hash: Mapped[str | None] = mapped_column(String(64))
    # Full-text search over title + description in a language-neutral configuration (NL and FR vacancies).
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('simple', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('simple', coalesce(description, '')), 'B')",
            persisted=True,
        ),
    )

    company: Mapped[Company] = relationship(back_populates="jobs")
    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True, order_by="JobSkill.position"
    )


class JobSkill(IdMixin, Base):
    __tablename__ = "job_skills"
    __table_args__ = (UniqueConstraint("job_id", "normalized_name", name="uq_job_skills_job_normalized"),)

    job_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("jobs.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    normalized_name: Mapped[str] = mapped_column(String(100), index=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped[Job] = relationship(back_populates="skills")


class SavedJob(IdMixin, Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_saved_jobs_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("jobs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship()


class JobView(IdMixin, Base):
    __tablename__ = "job_views"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_views_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("jobs.id"))
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship()


# ── CVs ──────────────────────────────────────────────────────────────────────


class CVDocument(IdMixin, TimestampMixin, Base):
    """An uploaded source CV. The file itself sits in private storage under an opaque key."""

    __tablename__ = "cv_documents"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str | None] = mapped_column(String(80))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    language: Mapped[str | None] = mapped_column(String(2))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(enum_type(ExtractionStatus), default=ExtractionStatus.PENDING)
    extraction_method: Mapped[str | None] = mapped_column(String(20))
    extraction_error: Mapped[str | None] = mapped_column(String(500))
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    analyses: Mapped[list["CVAnalysis"]] = relationship(back_populates="cv_document", cascade="all, delete-orphan", passive_deletes=True)


class CVAnalysis(IdMixin, Base):
    __tablename__ = "cv_analyses"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    cv_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, fk("cv_documents.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    method: Mapped[str] = mapped_column(String(20))
    quality_score: Mapped[int | None] = mapped_column(Integer)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    strengths: Mapped[list[str]] = mapped_column(JSONB, default=list)
    suggestions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    provider: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    cv_document: Mapped[CVDocument | None] = relationship(back_populates="analyses")


class CVVersion(IdMixin, TimestampMixin, Base):
    """A CV as a structured document (`app.schemas.cv.CVContent`).

    `generated_content` is what the optimizer produced and never changes; `content` holds the user's edits.
    The source CV document is never modified."""

    __tablename__ = "cv_versions"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    source_cv_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, fk("cv_documents.id", "SET NULL"))
    target_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, fk("jobs.id", "SET NULL"), index=True)
    kind: Mapped[CVVersionKind] = mapped_column(enum_type(CVVersionKind))
    status: Mapped[CVVersionStatus] = mapped_column(enum_type(CVVersionStatus), default=CVVersionStatus.READY)
    title: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(2), default="nl")
    template: Mapped[str] = mapped_column(String(30), default="modern")
    content: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    generated_content: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    source_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    optimization: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    match_before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    match_after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    provider: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(80))
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(String(500))
    user_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    export_count: Mapped[int] = mapped_column(Integer, default=0)
    last_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_export_format: Mapped[str | None] = mapped_column(String(10))

    target_job: Mapped[Job | None] = relationship()


# ── Matching ─────────────────────────────────────────────────────────────────


class JobMatch(IdMixin, Base):
    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_matches_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("jobs.id"), index=True)
    score: Mapped[int | None] = mapped_column(Integer, index=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    algorithm_version: Mapped[str] = mapped_column(String(20))
    input_hash: Mapped[str] = mapped_column(String(64))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Applications ─────────────────────────────────────────────────────────────


class Application(IdMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("jobs.id"), index=True)
    cv_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, fk("cv_versions.id", "SET NULL"))
    status: Mapped[ApplicationStatus] = mapped_column(enum_type(ApplicationStatus), index=True)
    channel: Mapped[ApplicationChannel] = mapped_column(enum_type(ApplicationChannel))
    notes: Mapped[str | None] = mapped_column(Text)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shared_with_employer_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped[Job] = relationship()
    user: Mapped[User] = relationship()
    cv_version: Mapped[CVVersion | None] = relationship()
    history: Mapped[list["ApplicationStatusHistory"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", passive_deletes=True, order_by="ApplicationStatusHistory.created_at"
    )


class ApplicationStatusHistory(IdMixin, Base):
    __tablename__ = "application_status_history"

    application_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("applications.id"), index=True)
    from_status: Mapped[ApplicationStatus | None] = mapped_column(enum_type(ApplicationStatus, "from_status"))
    to_status: Mapped[ApplicationStatus] = mapped_column(enum_type(ApplicationStatus, "to_status"))
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, fk("users.id", "SET NULL"))
    changed_by_role: Mapped[str | None] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="history")


# ── Platform ─────────────────────────────────────────────────────────────────


class Notification(IdMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(String(1000))
    link: Mapped[str | None] = mapped_column(String(300))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AIUsageRecord(IdMixin, Base):
    """Operational metadata about AI calls. Never stores prompts or responses (they contain CV data)."""

    __tablename__ = "ai_usage_records"

    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, fk("users.id", "SET NULL"), index=True)
    operation: Mapped[str] = mapped_column(String(50))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean)
    error_code: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, fk("users.id", "SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[str | None] = mapped_column(String(64))
    ip_hash: Mapped[str | None] = mapped_column(String(16))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class BackgroundTask(IdMixin, Base):
    """Durable task queue in PostgreSQL (claimed with SELECT ... FOR UPDATE SKIP LOCKED by the worker)."""

    __tablename__ = "background_tasks"
    __table_args__ = (Index("ix_background_tasks_claim", "status", "run_after"),)

    type: Mapped[str] = mapped_column(String(50))
    status: Mapped[TaskStatus] = mapped_column(enum_type(TaskStatus), default=TaskStatus.QUEUED)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, fk("users.id"), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=2)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=600)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str | None] = mapped_column(String(200))
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssistantMessage(IdMixin, Base):
    __tablename__ = "assistant_messages"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    job_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


__all__ = [
    "AIUsageRecord",
    "Application",
    "ApplicationStatusHistory",
    "AssistantMessage",
    "AuditLog",
    "AuthToken",
    "BackgroundTask",
    "CVAnalysis",
    "CVDocument",
    "CVVersion",
    "CandidatePreference",
    "CandidateProfile",
    "Company",
    "CompanyMembership",
    "Job",
    "JobMatch",
    "JobSkill",
    "JobView",
    "Notification",
    "SavedJob",
    "User",
    "UserSession",
]
