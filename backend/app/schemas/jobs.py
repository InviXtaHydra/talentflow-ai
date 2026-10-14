import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import (
    EducationLevel,
    EmploymentType,
    ExperienceLevel,
    JobStatus,
    RemotePolicy,
    SalaryPeriod,
)
from app.schemas.common import ApiModel, LongText, MediumText, ShortText


def _http_url(value: str | None) -> str | None:
    if value and not value.lower().startswith(("https://", "http://")):
        raise ValueError("Gebruik een volledige link die begint met https://")
    return value


class CompanyIn(BaseModel):
    name: ShortText = Field(min_length=2)
    description: LongText | None = None
    website_url: ShortText | None = None
    industry: ShortText | None = None
    city: ShortText | None = None
    size: Literal["1-10", "11-50", "51-200", "201-1000", "1000+"] | None = None

    @field_validator("website_url")
    @classmethod
    def valid_url(cls, value: str | None) -> str | None:
        return _http_url(value)


class CompanyUpdate(BaseModel):
    name: ShortText | None = Field(default=None, min_length=2)
    description: LongText | None = None
    website_url: ShortText | None = None
    industry: ShortText | None = None
    city: ShortText | None = None
    size: Literal["1-10", "11-50", "51-200", "201-1000", "1000+"] | None = None

    @field_validator("website_url")
    @classmethod
    def valid_url(cls, value: str | None) -> str | None:
        return _http_url(value)


class CompanyBrief(ApiModel):
    id: uuid.UUID
    name: str
    slug: str
    city: str | None = None
    industry: str | None = None
    logo_url: str | None = None
    is_demo: bool = False


class CompanyOut(CompanyBrief):
    description: str | None
    website_url: str | None
    size: str | None
    open_jobs: int = 0
    created_at: datetime
    viewer_role: str | None = None


class MemberOut(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    role: str


class AddMemberRequest(BaseModel):
    email: str = Field(max_length=320)
    role: Literal["owner", "recruiter"] = "recruiter"


class JobSkillIn(BaseModel):
    name: ShortText = Field(min_length=1, max_length=100)
    is_required: bool = True


class JobSkillOut(BaseModel):
    name: str
    is_required: bool


class _JobFields(BaseModel):
    title: ShortText = Field(min_length=3)
    description: LongText = Field(min_length=20)
    responsibilities: list[MediumText] = Field(default_factory=list, max_length=30)
    qualifications: list[MediumText] = Field(default_factory=list, max_length=30)
    benefits: list[MediumText] = Field(default_factory=list, max_length=30)
    about_team: LongText | None = None
    hiring_process: list[MediumText] = Field(default_factory=list, max_length=10)
    department: ShortText | None = None
    hours_per_week: int | None = Field(default=None, ge=1, le=60)
    contract_duration_months: int | None = Field(default=None, ge=1, le=60)
    start_date: date | None = None
    openings: int = Field(default=1, ge=1, le=100)
    skills: list[JobSkillIn] = Field(default_factory=list, max_length=40)
    min_years_experience: int | None = Field(default=None, ge=0, le=40)
    experience_level: ExperienceLevel | None = None
    education_level: EducationLevel | None = None
    required_languages: list[str] = Field(default_factory=list, max_length=6)
    city: ShortText | None = None
    remote_policy: RemotePolicy = RemotePolicy.ONSITE
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    salary_min: int | None = Field(default=None, ge=0, le=1_000_000)
    salary_max: int | None = Field(default=None, ge=0, le=1_000_000)
    salary_currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    salary_period: SalaryPeriod | None = None
    industry: ShortText | None = None
    language: Literal["nl", "fr", "en"] = "nl"
    application_deadline: date | None = None
    application_url: ShortText | None = None

    @field_validator("application_url")
    @classmethod
    def valid_url(cls, value: str | None) -> str | None:
        return _http_url(value)

    @field_validator("required_languages")
    @classmethod
    def lower_codes(cls, values: list[str]) -> list[str]:
        return sorted({v.strip().lower() for v in values if v.strip()})

    @model_validator(mode="after")
    def salary_consistent(self) -> "_JobFields":
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("Het minimumloon mag niet hoger zijn dan het maximum.")
        if (self.salary_min is not None or self.salary_max is not None) and self.salary_period is None:
            raise ValueError("Geef aan of het loon per jaar, maand of uur is.")
        return self


class JobIn(_JobFields):
    status: Literal["draft", "published"] = "draft"


class JobUpdate(BaseModel):
    """Partial update: fields that are sent replace the stored values."""

    title: ShortText | None = Field(default=None, min_length=3)
    description: LongText | None = Field(default=None, min_length=20)
    responsibilities: list[MediumText] | None = None
    qualifications: list[MediumText] | None = None
    benefits: list[MediumText] | None = None
    about_team: LongText | None = None
    hiring_process: list[MediumText] | None = None
    department: ShortText | None = None
    hours_per_week: int | None = Field(default=None, ge=1, le=60)
    contract_duration_months: int | None = Field(default=None, ge=1, le=60)
    start_date: date | None = None
    openings: int | None = Field(default=None, ge=1, le=100)
    skills: list[JobSkillIn] | None = None
    min_years_experience: int | None = Field(default=None, ge=0, le=40)
    experience_level: ExperienceLevel | None = None
    education_level: EducationLevel | None = None
    required_languages: list[str] | None = None
    city: ShortText | None = None
    remote_policy: RemotePolicy | None = None
    employment_type: EmploymentType | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    salary_period: SalaryPeriod | None = None
    industry: ShortText | None = None
    language: Literal["nl", "fr", "en"] | None = None
    application_deadline: date | None = None
    application_url: ShortText | None = None
    status: JobStatus | None = None

    @field_validator("application_url")
    @classmethod
    def valid_url(cls, value: str | None) -> str | None:
        return _http_url(value)


class MatchBrief(BaseModel):
    score: int | None
    status: str
    matching_skills: list[str]
    missing_required_skills: list[str]
    strongest_factors: list[str]
    eligibility: str
    stale: bool = False


class JobSummaryOut(BaseModel):
    id: uuid.UUID
    title: str
    company: CompanyBrief
    city: str | None
    remote_policy: RemotePolicy
    employment_type: EmploymentType
    experience_level: ExperienceLevel | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str
    salary_period: SalaryPeriod | None
    industry: str | None
    language: str
    status: JobStatus
    published_at: datetime | None
    application_deadline: date | None
    is_demo: bool
    skills: list[JobSkillOut]
    saved: bool = False
    match: MatchBrief | None = None


class ApplicationBrief(BaseModel):
    id: uuid.UUID
    status: str
    channel: str


class CompanyProfileOut(BaseModel):
    description: str | None
    website_url: str | None
    size: str | None
    open_jobs: int


class RecruiterOut(BaseModel):
    full_name: str


class JobDetailOut(JobSummaryOut):
    description: str
    responsibilities: list[str]
    qualifications: list[str]
    benefits: list[str]
    about_team: str | None
    hiring_process: list[str]
    department: str | None
    hours_per_week: int | None
    contract_duration_months: int | None
    start_date: date | None
    openings: int
    company_profile: CompanyProfileOut
    recruiter: RecruiterOut | None
    applicant_count: int
    view_count: int
    min_years_experience: int | None
    education_level: EducationLevel | None
    required_languages: list[str]
    application_url: str | None
    source: str
    created_at: datetime
    updated_at: datetime
    application: ApplicationBrief | None = None
    can_edit: bool = False


class MatchOut(BaseModel):
    job_id: uuid.UUID
    score: int | None
    status: str
    result: dict[str, Any]
    algorithm_version: str
    calculated_at: datetime
    weights: dict[str, float]


class JobSearchParams(BaseModel):
    q: str | None = Field(default=None, max_length=200)
    company_id: uuid.UUID | None = None
    city: str | None = Field(default=None, max_length=120)
    max_distance_km: int | None = Field(default=None, ge=1, le=300)
    remote: list[RemotePolicy] = Field(default_factory=list)
    employment_type: list[EmploymentType] = Field(default_factory=list)
    experience_level: list[ExperienceLevel] = Field(default_factory=list)
    industry: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    salary_min_annual: int | None = Field(default=None, ge=0)
    language: list[str] = Field(default_factory=list)
    sort: Literal["relevance", "date", "salary", "match"] = "relevance"
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=20, ge=1, le=50)


class FacetsOut(BaseModel):
    industries: list[str]
    cities: list[str]
    skills: list[str]
