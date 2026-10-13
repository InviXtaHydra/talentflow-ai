"""Flat, simple output schema for CV extraction by a language model.

Every field is required (but may be null or empty): with optional fields, small models tend to return
the shortest valid JSON instead of filling in the CV.

Small local models fill flat schemas with descriptions far more reliably than the nested internal model
(with ids and defaults). The result is converted to `ExtractedCV` and validated again."""

from pydantic import BaseModel, Field

from app.schemas.profile import ContactDetails, ExtractedCV, LanguageSkill, ProfileContent
from app.utils.skills import looks_like_internship, split_skills


class LlmExperience(BaseModel):
    job_title: str = Field(description="Job title exactly as written")
    employer: str = Field(description="Company or organisation name")
    location: str | None = Field(description="City, if mentioned")
    start: str | None = Field(description="Start date copied exactly as written in the CV, e.g. 'Sep 2024' or '03/2021'")
    end: str | None = Field(description="End date copied exactly as written, e.g. 'May 2025'; null if current")
    current: bool = Field(description="True if this is the current job")
    internship: bool = Field(description="True if this position is an internship (stage, stagiair, intern, trainee)")
    bullets: list[str] = Field(description="Each responsibility or achievement, copied from the CV")


class LlmEducation(BaseModel):
    degree: str = Field(description="Degree or programme name")
    institution: str = Field(description="School or university")
    level: str | None = Field(description="secondary | professional_bachelor | bachelor | master | phd")
    start: str | None
    end: str | None


class LlmLanguage(BaseModel):
    code: str = Field(description="ISO 639-1 code, e.g. nl, fr, en")
    level: str = Field(description="native | fluent | professional | basic")


class LlmCertification(BaseModel):
    name: str
    issuer: str | None
    year: int | None


class LlmProject(BaseModel):
    name: str
    description: str | None
    technologies: list[str] = Field()


class LlmCV(BaseModel):
    full_name: str | None = Field(description="The candidate's full name, usually at the top of the CV")
    email: str | None
    phone: str | None
    city: str | None = Field(description="Where the candidate lives")
    linkedin_url: str | None
    website_url: str | None
    headline: str | None = Field(description="Professional title under the name, if any")
    summary: str | None = Field(description="The profile/summary paragraph, copied")
    experiences: list[LlmExperience] = Field(description="Every job in the work experience section")
    education: list[LlmEducation] = Field()
    skills: list[str] = Field(description="Every skill, tool and technology listed")
    languages: list[LlmLanguage] = Field()
    certifications: list[LlmCertification] = Field()
    projects: list[LlmProject] = Field()
    cv_language: str | None = Field(description="Language the CV is written in: nl, fr or en")


_LEVELS = {"secondary", "professional_bachelor", "bachelor", "master", "phd"}


_MONTHS = {
    "jan": 1,
    "januari": 1,
    "january": 1,
    "janvier": 1,
    "janv": 1,
    "feb": 2,
    "februari": 2,
    "february": 2,
    "fevrier": 2,
    "février": 2,
    "fev": 2,
    "fév": 2,
    "févr": 2,
    "mrt": 3,
    "maart": 3,
    "mar": 3,
    "march": 3,
    "mars": 3,
    "apr": 4,
    "april": 4,
    "avril": 4,
    "avr": 4,
    "mei": 5,
    "may": 5,
    "mai": 5,
    "jun": 6,
    "juni": 6,
    "june": 6,
    "juin": 6,
    "jul": 7,
    "juli": 7,
    "july": 7,
    "juillet": 7,
    "juil": 7,
    "aug": 8,
    "augustus": 8,
    "august": 8,
    "aout": 8,
    "août": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "septembre": 9,
    "okt": 10,
    "oct": 10,
    "oktober": 10,
    "october": 10,
    "octobre": 10,
    "nov": 11,
    "november": 11,
    "novembre": 11,
    "dec": 12,
    "december": 12,
    "décembre": 12,
    "decembre": 12,
    "déc": 12,
}
_PRESENT = ("heden", "present", "current", "now", "today", "aujourd", "actuel", "en cours")


def is_present(value: str | None) -> bool:
    return bool(value) and any(word in str(value).lower() for word in _PRESENT)


def _ym(value: str | None) -> str | None:
    """Normalizes dates like 'Sep 2024', 'september 2024', '2021-03', '03/2021' or '2021' to YYYY-MM / YYYY."""
    import re

    if not value or is_present(value):
        return None
    text = value.lower()
    if (match := re.search(r"([a-zéû]{3,10})\.?\s*'?(\d{4})", text)) and (month := _MONTHS.get(match.group(1))):
        return f"{match.group(2)}-{month:02d}"
    if match := re.search(r"\b(\d{4})[-/.](\d{1,2})\b", text):
        year, month_text = match.group(1), match.group(2)
    elif match := re.search(r"\b(\d{1,2})[-/.](\d{4})\b", text):
        month_text, year = match.group(1), match.group(2)
    elif match := re.search(r"\b(\d{4})\b", text):
        return match.group(1)
    else:
        return None
    return f"{year}-{int(month_text):02d}" if 1 <= int(month_text) <= 12 else year


def to_extracted(cv: LlmCV) -> ExtractedCV:
    profile = ProfileContent.model_validate(
        {
            "experiences": [
                {
                    "title": e.job_title[:200],
                    "employer": e.employer[:200],
                    "location": e.location,
                    "start": _ym(e.start),
                    "end": None if e.current or is_present(e.end) else _ym(e.end),
                    "is_current": e.current or is_present(e.end),
                    "is_internship": e.internship or looks_like_internship(e.job_title, e.employer),
                    "bullets": [b[:1000] for b in e.bullets if b.strip()][:30],
                }
                for e in cv.experiences
                if e.job_title.strip() and e.employer.strip()
            ],
            "education": [
                {
                    "degree": e.degree[:200],
                    "institution": e.institution[:200],
                    "level": e.level if e.level in _LEVELS else None,
                    "start": _ym(e.start),
                    "end": _ym(e.end),
                }
                for e in cv.education
                if e.degree.strip() and e.institution.strip()
            ],
            "skills": split_skills([s for s in cv.skills if s.strip()])[:80],
            "languages": [LanguageSkill(code=lang.code, level=lang.level) for lang in cv.languages if 2 <= len(lang.code.strip()) <= 12][
                :15
            ],
            "certifications": [
                {"name": c.name[:200], "issuer": c.issuer, "year": c.year if c.year and 1950 <= c.year <= 2100 else None}
                for c in cv.certifications
                if c.name.strip()
            ],
            "projects": [
                {"name": p.name[:200], "description": (p.description or "")[:1000] or None, "technologies": p.technologies[:30]}
                for p in cv.projects
                if p.name.strip()
            ],
        }
    )
    return ExtractedCV(
        language=cv.cv_language if cv.cv_language in ("nl", "fr", "en") else None,
        contact=ContactDetails(
            full_name=cv.full_name, email=cv.email, phone=cv.phone, city=cv.city, linkedin_url=cv.linkedin_url, website_url=cv.website_url
        ),
        # A "headline" longer than a title is usually the summary paragraph picked up twice.
        headline=cv.headline if cv.headline and len(cv.headline) <= 100 and cv.headline != cv.summary else None,
        summary=(cv.summary or "")[:10000] or None,
        profile=profile,
    )
