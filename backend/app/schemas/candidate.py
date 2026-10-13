import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import EmploymentType, RemotePreference, SalaryPeriod
from app.schemas.common import ApiModel, LongText, ShortText
from app.schemas.profile import ProfileContent


class CandidateProfileOut(ApiModel):
    id: uuid.UUID
    full_name: str
    email: str
    headline: str | None
    summary: str | None
    phone: str | None
    city: str | None
    linkedin_url: str | None
    website_url: str | None
    content: ProfileContent
    onboarding_completed_at: datetime | None
    confirmed_at: datetime | None
    updated_at: datetime
    is_demo: bool


class CandidateProfileUpdate(BaseModel):
    headline: ShortText | None = None
    summary: LongText | None = None
    phone: ShortText | None = None
    city: ShortText | None = None
    linkedin_url: ShortText | None = None
    website_url: ShortText | None = None
    content: ProfileContent | None = None
    complete_onboarding: bool = False


class PreferencesIn(BaseModel):
    desired_titles: list[ShortText] = Field(default_factory=list, max_length=10)
    preferred_locations: list[ShortText] = Field(default_factory=list, max_length=10)
    max_commute_km: int | None = Field(default=None, ge=0, le=500)
    remote_preference: RemotePreference = RemotePreference.ANY
    employment_types: list[EmploymentType] = Field(default_factory=list)
    salary_min: int | None = Field(default=None, ge=0, le=1_000_000)
    salary_currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    salary_period: SalaryPeriod = SalaryPeriod.MONTH
    industries: list[ShortText] = Field(default_factory=list, max_length=10)
    languages: list[str] = Field(default_factory=list, max_length=10)
    available_from: date | None = None
    availability_note: ShortText | None = None

    @field_validator("desired_titles", "preferred_locations", "industries")
    @classmethod
    def drop_empty(cls, values: list[str]) -> list[str]:
        return [v for v in values if v]


class PreferencesOut(PreferencesIn, ApiModel):
    updated_at: datetime
