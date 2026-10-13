"""Turns database records into the plain facts the matching engine works with."""

from app.models.entities import CandidatePreference, CandidateProfile, Job
from app.models.enums import EducationLevel, RemotePreference
from app.schemas.cv import CVContent
from app.schemas.profile import ProfileContent
from app.services.matching.engine import CandidateFacts, ExperienceFact, JobFacts, PreferenceFacts
from app.utils.salary import to_annual_eur
from app.utils.skills import looks_like_internship, normalize_skill, split_skills

_EDU_RANK = {
    EducationLevel.NONE: 0,
    EducationLevel.SECONDARY: 1,
    EducationLevel.PROFESSIONAL_BACHELOR: 2,
    EducationLevel.BACHELOR: 2,
    EducationLevel.MASTER: 3,
    EducationLevel.PHD: 4,
}


def preference_facts(prefs: CandidatePreference | None) -> PreferenceFacts:
    if prefs is None:
        return PreferenceFacts()
    return PreferenceFacts(
        locations=list(prefs.preferred_locations or []),
        max_commute_km=prefs.max_commute_km,
        remote=RemotePreference(prefs.remote_preference),
        employment_types=list(prefs.employment_types or []),
        salary_min_annual_eur=to_annual_eur(prefs.salary_min, prefs.salary_period, prefs.salary_currency),
        industries=list(prefs.industries or []),
    )


def _highest_education(levels: list[EducationLevel | None]) -> EducationLevel | None:
    known = [lvl for lvl in levels if lvl is not None]
    return max(known, key=lambda lvl: _EDU_RANK[lvl]) if known else None


def candidate_facts(profile: CandidateProfile | None, prefs: CandidatePreference | None, *, use_embedding: bool = True) -> CandidateFacts:
    content = ProfileContent.model_validate(profile.content if profile and profile.content else {})
    experiences = [
        ExperienceFact(
            id=e.id,
            title=e.title,
            employer=e.employer,
            text=" ".join([e.description or "", *e.bullets]),
            start=e.start,
            end=e.end,
            is_current=e.is_current,
            is_internship=e.is_internship or looks_like_internship(e.title, e.employer),
        )
        for e in content.experiences
    ]
    titles = [e.title for e in content.experiences]
    if profile and profile.headline:
        titles.append(profile.headline)
    if prefs:
        titles.extend(prefs.desired_titles or [])
    skills = {normalize_skill(s): s for s in split_skills(content.skills)}
    for project in content.projects:
        for tech in project.technologies:
            skills.setdefault(normalize_skill(tech), tech)
    profile_text = (
        " ".join([profile.headline or "", profile.summary or ""] if profile else [])
        + " "
        + " ".join(f"{e.title} {e.text}" for e in experiences)
        + " "
        + " ".join(content.skills)
    )
    return CandidateFacts(
        skills=skills,
        experiences=experiences,
        titles=titles,
        profile_text=profile_text,
        education_level=_highest_education([e.level for e in content.education]),
        languages={lang.code: lang.level for lang in content.languages},
        preferences=preference_facts(prefs),
        city=profile.city if profile else None,
        embedding=list(profile.embedding) if use_embedding and profile is not None and profile.embedding is not None else None,
        skills_text=" | ".join(content.skills),
    )


def cv_candidate_facts(cv: CVContent, base: CandidateFacts) -> CandidateFacts:
    """Facts as presented by a (tailored) CV. Education level, languages and preferences come from the
    verified profile (`base`); experience and skills only count what the CV actually states."""
    experiences = [
        ExperienceFact(
            id=e.source_id or f"cv-{i}",
            title=e.title,
            employer=e.employer,
            text=" ".join(b.text for b in e.bullets),
            start=e.start,
            end=e.end,
            is_current=e.is_current,
            is_internship=next(
                (b.is_internship for b in base.experiences if b.id == e.source_id), looks_like_internship(e.title, e.employer)
            ),
        )
        for i, e in enumerate(cv.experiences)
    ]
    skills = {normalize_skill(s): s for s in split_skills(cv.skills)}
    for project in cv.projects:
        for tech in project.technologies:
            skills.setdefault(normalize_skill(tech), tech)
    titles = [e.title for e in cv.experiences] + ([cv.headline] if cv.headline else [])
    text = (
        " ".join([cv.headline or "", cv.summary or ""])
        + " "
        + " ".join(f"{e.title} {e.text}" for e in experiences)
        + " "
        + " ".join(cv.skills)
    )
    return CandidateFacts(
        skills=skills,
        experiences=experiences,
        titles=titles,
        profile_text=text,
        education_level=base.education_level,
        languages=base.languages,
        preferences=base.preferences,
        city=base.city,
        embedding=None,
        skills_text=" | ".join(cv.skills),
    )


def job_facts(job: Job, *, use_embedding: bool = True) -> JobFacts:
    required = {s.normalized_name: s.name for s in job.skills if s.is_required}
    preferred = {s.normalized_name: s.name for s in job.skills if not s.is_required and s.normalized_name not in required}
    text = " ".join([job.title, job.description, *(job.responsibilities or []), *(job.qualifications or [])])
    return JobFacts(
        id=str(job.id),
        title=job.title,
        text=text,
        required_skills=required,
        preferred_skills=preferred,
        min_years=job.min_years_experience,
        experience_level=job.experience_level,
        education_level=job.education_level,
        required_languages=list(job.required_languages or []),
        city=job.city,
        remote_policy=job.remote_policy,
        employment_type=job.employment_type.value,
        salary_annual_min_eur=job.salary_annual_min_eur,
        salary_annual_max_eur=job.salary_annual_max_eur,
        industry=job.industry,
        embedding=list(job.embedding) if use_embedding and job.embedding is not None else None,
    )
