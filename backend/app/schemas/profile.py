"""The structured professional profile. Used for the confirmed profile, for CV extraction results
and as the factual source the CV optimizer must stay within."""

import uuid

from pydantic import BaseModel, Field, field_validator

from app.models.enums import EducationLevel
from app.schemas.common import LongText, MediumText, ShortText, YearMonth


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class Experience(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("exp"), max_length=40)
    title: ShortText
    employer: ShortText
    location: ShortText | None = None
    start: YearMonth | None = None
    end: YearMonth | None = None
    is_current: bool = False
    description: LongText | None = None
    bullets: list[MediumText] = Field(default_factory=list, max_length=30)


class Education(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("edu"), max_length=40)
    degree: ShortText
    institution: ShortText
    field: ShortText | None = None
    level: EducationLevel | None = None
    start: YearMonth | None = None
    end: YearMonth | None = None
    description: MediumText | None = None


class Certification(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("cert"), max_length=40)
    name: ShortText
    issuer: ShortText | None = None
    year: int | None = Field(default=None, ge=1950, le=2100)


LANGUAGE_LEVELS = ("native", "fluent", "professional", "basic")


class LanguageSkill(BaseModel):
    # ISO 639-1 code where known (nl, fr, en, de, tr, ...)
    code: str = Field(min_length=2, max_length=12)
    level: str = "professional"

    @field_validator("code")
    @classmethod
    def lower(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("level")
    @classmethod
    def known_level(cls, value: str) -> str:
        value = value.strip().lower()
        return value if value in LANGUAGE_LEVELS else "professional"


class Project(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("proj"), max_length=40)
    name: ShortText
    description: MediumText | None = None
    url: ShortText | None = None
    technologies: list[ShortText] = Field(default_factory=list, max_length=30)


class ProfileContent(BaseModel):
    experiences: list[Experience] = Field(default_factory=list, max_length=40)
    education: list[Education] = Field(default_factory=list, max_length=20)
    skills: list[ShortText] = Field(default_factory=list, max_length=80)
    certifications: list[Certification] = Field(default_factory=list, max_length=40)
    languages: list[LanguageSkill] = Field(default_factory=list, max_length=15)
    projects: list[Project] = Field(default_factory=list, max_length=30)

    @field_validator("skills")
    @classmethod
    def unique_skills(cls, skills: list[str]) -> list[str]:
        seen: set[str] = set()
        result = []
        for skill in skills:
            key = skill.lower()
            if skill and key not in seen:
                seen.add(key)
                result.append(skill)
        return result


class ContactDetails(BaseModel):
    full_name: ShortText | None = None
    email: ShortText | None = None
    phone: ShortText | None = None
    city: ShortText | None = None
    linkedin_url: ShortText | None = None
    website_url: ShortText | None = None


class ExtractedCV(BaseModel):
    """What the extractor found in an uploaded CV. Shown to the candidate for review; never trusted blindly."""

    language: str | None = None
    contact: ContactDetails = Field(default_factory=ContactDetails)
    headline: ShortText | None = None
    summary: LongText | None = None
    profile: ProfileContent = Field(default_factory=ProfileContent)
