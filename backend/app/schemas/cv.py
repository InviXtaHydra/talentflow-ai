"""Structured CV documents (stored on CVVersion.content) and the CV optimizer's output contract."""

from pydantic import BaseModel, Field

from app.schemas.common import LongText, MediumText, ShortText, YearMonth
from app.schemas.profile import ContactDetails, LanguageSkill

CV_TEMPLATES = ("modern", "minimal", "technical")
CV_LANGUAGES = ("nl", "fr", "en")


class CVBullet(BaseModel):
    text: MediumText
    # Ids of the profile items this statement is based on (e.g. "exp-1a2b3c4d"). Provenance for the fact check.
    source_refs: list[str] = Field(default_factory=list, max_length=10)


class CVExperience(BaseModel):
    source_id: str | None = None
    title: ShortText
    employer: ShortText
    location: ShortText | None = None
    start: YearMonth | None = None
    end: YearMonth | None = None
    is_current: bool = False
    bullets: list[CVBullet] = Field(default_factory=list, max_length=20)


class CVEducation(BaseModel):
    source_id: str | None = None
    degree: ShortText
    institution: ShortText
    field: ShortText | None = None
    start: YearMonth | None = None
    end: YearMonth | None = None
    description: MediumText | None = None


class CVCertification(BaseModel):
    source_id: str | None = None
    name: ShortText
    issuer: ShortText | None = None
    year: int | None = None


class CVProject(BaseModel):
    source_id: str | None = None
    name: ShortText
    description: MediumText | None = None
    url: ShortText | None = None
    technologies: list[ShortText] = Field(default_factory=list, max_length=30)


class CVContent(BaseModel):
    contact: ContactDetails = Field(default_factory=ContactDetails)
    headline: ShortText | None = None
    summary: LongText | None = None
    experiences: list[CVExperience] = Field(default_factory=list, max_length=40)
    education: list[CVEducation] = Field(default_factory=list, max_length=20)
    skills: list[ShortText] = Field(default_factory=list, max_length=80)
    certifications: list[CVCertification] = Field(default_factory=list, max_length=40)
    languages: list[LanguageSkill] = Field(default_factory=list, max_length=15)
    projects: list[CVProject] = Field(default_factory=list, max_length=30)


# ── What the language model must return for an optimization ────────────────


class OptimizedBullet(BaseModel):
    text: str = Field(
        max_length=600, description="Rewritten statement: action verb first, relevant to the vacancy, only facts from the source"
    )
    source_refs: list[str] = Field(description="Ids of the profile items this statement is based on")


class OptimizedExperience(BaseModel):
    source_id: str = Field(description="The id of the experience in the profile")
    bullets: list[OptimizedBullet] = Field(description="Rewritten bullets for this experience, most relevant first")


class OptimizedProject(BaseModel):
    source_id: str
    description: str | None = Field(max_length=800)


class ChangeNote(BaseModel):
    section: str = Field(max_length=40)
    description: str = Field(max_length=400)


class CandidateQuestion(BaseModel):
    question: str = Field(max_length=400)
    reason: str | None = Field(max_length=400)


class OptimizerOutput(BaseModel):
    """All fields are required (lists may be empty) so small models fill them in instead of returning minimal JSON.

    The model may only rephrase, select and reorder. Names, employers, titles, dates, education
    and contact details are copied from the source by the backend, not taken from this output."""

    headline: str | None = Field(max_length=200, description="Short professional title supported by the profile")
    summary: str = Field(
        max_length=2000,
        description="NEW 2-4 sentence CV profile for this kind of role, using only profile facts; no company name, no wish to apply",
    )
    summary_source_refs: list[str] = Field()
    experience_order: list[str] = Field(description="Experience ids, most relevant for the vacancy first")
    experiences: list[OptimizedExperience] = Field(description="One entry for EVERY experience in the profile")
    skills: list[str] = Field(description="Profile skills only, most relevant for the vacancy first")
    project_order: list[str] = Field()
    projects: list[OptimizedProject] = Field()
    emphasized_keywords: list[str] = Field()
    changes: list[ChangeNote] = Field(description="What was changed and why, one note per change")
    questions: list[CandidateQuestion] = Field(
        default_factory=list, description="Questions for facts that would strengthen the CV but are missing"
    )


class ReviewItem(BaseModel):
    """Content the model proposed that could not be traced back to the source profile."""

    kind: str  # "bullet" | "skill" | "summary" | "fact_restored"
    section: str
    text: str
    reason: str
    source_id: str | None = None


class GapAnalysis(BaseModel):
    matching_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    keywords_missing_from_cv: list[str] = Field(default_factory=list)
    relevant_experience_ids: list[str] = Field(default_factory=list)


class OptimizationReport(BaseModel):
    changes: list[ChangeNote] = Field(default_factory=list)
    emphasized_keywords: list[str] = Field(default_factory=list)
    questions: list[CandidateQuestion] = Field(default_factory=list)
    review_items: list[ReviewItem] = Field(default_factory=list)
    gap: GapAnalysis = Field(default_factory=GapAnalysis)
    target_language: str = "nl"
    summary_text: LongText | None = None
