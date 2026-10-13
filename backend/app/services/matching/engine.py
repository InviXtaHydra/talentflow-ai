"""Explainable job matching.

The score is computed here, deterministically, from structured profile and vacancy data. A language
model is never asked to invent a percentage. See docs/ai-matching.md for the full description.

Design rules:
- Five weighted components (skills, experience, role, qualifications, preferences).
- A component that cannot be evaluated (missing data on either side) is *not applicable*: it is
  left out and the remaining weights are renormalized, instead of counting it as a mismatch.
- Hard requirements (required languages, minimum education, far too little experience) are shown
  separately as eligibility issues and cap the overall score, so semantic similarity can never hide them.
- Sensitive characteristics (age, gender, origin, photo, ...) are not inputs at all.
"""

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from app.core.config import MatchingWeights
from app.models.enums import EducationLevel, ExperienceLevel, RemotePolicy, RemotePreference
from app.utils import geo
from app.utils.skills import text_mentions_skill
from app.utils.text import tokens

ALGORITHM_VERSION = "1.3.0"

# Score cap when a hard requirement is clearly not met.
HARD_REQUIREMENT_CAP = 60

_LEVEL_YEARS = {ExperienceLevel.JUNIOR: 0, ExperienceLevel.MEDIOR: 2, ExperienceLevel.SENIOR: 5, ExperienceLevel.LEAD: 8}
_EDUCATION_RANK = {
    EducationLevel.NONE: 0,
    EducationLevel.SECONDARY: 1,
    EducationLevel.PROFESSIONAL_BACHELOR: 2,
    EducationLevel.BACHELOR: 2,
    EducationLevel.MASTER: 3,
    EducationLevel.PHD: 4,
}
_LANGUAGE_LEVEL_OK = {"native", "fluent", "professional"}

# Calibration of cosine similarity for nomic-embed-text: unrelated texts land around 0.45,
# closely related role descriptions around 0.80.
_EMBEDDING_FLOOR = 0.45
_EMBEDDING_CEILING = 0.80


@dataclass
class ExperienceFact:
    id: str
    title: str
    employer: str
    text: str
    start: str | None
    end: str | None
    is_current: bool


@dataclass
class PreferenceFacts:
    locations: list[str] = field(default_factory=list)
    max_commute_km: int | None = None
    remote: RemotePreference = RemotePreference.ANY
    employment_types: list[str] = field(default_factory=list)
    salary_min_annual_eur: int | None = None
    industries: list[str] = field(default_factory=list)


@dataclass
class CandidateFacts:
    skills: dict[str, str]  # normalized -> display name
    experiences: list[ExperienceFact]
    titles: list[str]
    profile_text: str
    education_level: EducationLevel | None
    languages: dict[str, str]  # code -> level
    preferences: PreferenceFacts
    city: str | None = None
    embedding: list[float] | None = None


@dataclass
class JobFacts:
    id: str
    title: str
    text: str
    required_skills: dict[str, str]  # normalized -> display
    preferred_skills: dict[str, str]
    min_years: int | None
    experience_level: ExperienceLevel | None
    education_level: EducationLevel | None
    required_languages: list[str]
    city: str | None
    remote_policy: RemotePolicy
    employment_type: str
    salary_annual_min_eur: int | None
    salary_annual_max_eur: int | None
    industry: str | None
    embedding: list[float] | None = None


Status = Literal["match", "partial", "mismatch", "unknown"]


def _component(key: str, weight: float, score: float | None, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": key,
        "weight": weight,
        "applicable": score is not None,
        "score": None if score is None else round(max(0.0, min(1.0, score)) * 100),
        "details": details,
    }


# ── helpers ─────────────────────────────────────────────────────────────────


def _parse_ym(value: str | None, *, end: bool) -> tuple[int, int] | None:
    if not value:
        return None
    parts = value.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else (12 if end else 1)
    return year, month


def experience_months(exp: ExperienceFact, today: date) -> tuple[int, int] | None:
    """Returns (start_index, end_index) in months, or None when the start date is unknown."""
    start = _parse_ym(exp.start, end=False)
    if start is None:
        return None
    end = (today.year, today.month) if exp.is_current or not exp.end else _parse_ym(exp.end, end=True)
    assert end is not None
    s = start[0] * 12 + start[1] - 1
    e = end[0] * 12 + end[1]  # inclusive end month
    return (s, e) if e > s else None


def _merged_months(intervals: list[tuple[int, int]]) -> int:
    """Total months covered, counting overlapping jobs only once."""
    total, current_start, current_end = 0, None, None
    for start, end in sorted(intervals):
        if current_end is None or start > current_end:
            if current_end is not None and current_start is not None:
                total += current_end - current_start
            current_start, current_end = start, end
        else:
            current_end = max(current_end, end)
    if current_end is not None and current_start is not None:
        total += current_end - current_start
    return total


def _dice(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return 2 * len(sa & sb) / (len(sa) + len(sb))


def _tf_cosine(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    va: dict[str, int] = {}
    vb: dict[str, int] = {}
    for t in a:
        va[t] = va.get(t, 0) + 1
    for t in b:
        vb[t] = vb.get(t, 0) + 1
    dot = sum(v * vb.get(k, 0) for k, v in va.items())
    norm = math.sqrt(sum(v * v for v in va.values())) * math.sqrt(sum(v * v for v in vb.values()))
    return dot / norm if norm else 0.0


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def title_similarity(candidate_titles: list[str], job_title: str) -> float:
    job_tokens = tokens(job_title)
    return max((_dice(tokens(t), job_tokens) for t in candidate_titles if t), default=0.0)


# ── components ──────────────────────────────────────────────────────────────


def _candidate_has_skill(candidate: CandidateFacts, skill: str) -> str | None:
    """'listed' when on the skills list, 'experience' when only evidenced in work experience, else None."""
    if skill in candidate.skills:
        return "listed"
    for exp in candidate.experiences:
        if text_mentions_skill(f"{exp.title} {exp.text}", skill):
            return "experience"
    return None


def score_skills(candidate: CandidateFacts, job: JobFacts, weight: float) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]]]:
    matched: list[dict[str, str]] = []
    missing_required: list[dict[str, str]] = []
    missing_preferred: list[dict[str, str]] = []
    points = possible = 0.0
    for skills, is_required, factor in ((job.required_skills, True, 2.0), (job.preferred_skills, False, 1.0)):
        for normalized, display in skills.items():
            possible += factor
            evidence = _candidate_has_skill(candidate, normalized)
            if evidence:
                points += factor
                matched.append({"name": display, "evidence": evidence, "required": "yes" if is_required else "no"})
            elif is_required:
                missing_required.append({"name": display})
            else:
                missing_preferred.append({"name": display})
    has_candidate_data = bool(candidate.skills or candidate.experiences)
    score = points / possible if possible and has_candidate_data else None
    details = {
        "matched": len(matched),
        "total": len(job.required_skills) + len(job.preferred_skills),
        "required_matched": sum(1 for m in matched if m["required"] == "yes"),
        "required_total": len(job.required_skills),
        "reason": None if score is not None else ("no_job_skills" if not possible else "no_candidate_skills"),
    }
    return _component("skills", weight, score, details), {
        "matching": matched,
        "missing_required": missing_required,
        "missing_preferred": missing_preferred,
    }


def score_experience(candidate: CandidateFacts, job: JobFacts, weight: float, today: date) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    required_years = (
        job.min_years if job.min_years is not None else (_LEVEL_YEARS.get(job.experience_level) if job.experience_level else None)
    )
    job_skill_keys = list(job.required_skills) + list(job.preferred_skills)
    relevant: list[dict[str, Any]] = []
    intervals: list[tuple[int, int]] = []
    all_intervals: list[tuple[int, int]] = []
    for exp in candidate.experiences:
        span = experience_months(exp, today)
        if span:
            all_intervals.append(span)
        text = f"{exp.title} {exp.text}"
        skill_hits = [k for k in job_skill_keys if text_mentions_skill(text, k)]
        title_sim = _dice(tokens(exp.title), tokens(job.title))
        if title_sim >= 0.3 or skill_hits:
            months = (span[1] - span[0]) if span else None
            relevant.append({"id": exp.id, "title": exp.title, "employer": exp.employer, "months": months, "skills": len(skill_hits)})
            if span:
                intervals.append(span)

    relevant_years = round(_merged_months(intervals) / 12, 1)
    total_years = round(_merged_months(all_intervals) / 12, 1)
    if not candidate.experiences:
        score = 1.0 if required_years == 0 else None
        reason = None if score is not None else "no_candidate_experience"
    elif required_years is None:
        score = 1.0 if relevant else 0.5
        reason = None
    elif required_years == 0:
        score = 1.0
        reason = None
    else:
        score = min(1.0, relevant_years / required_years)
        reason = None
    details = {
        "required_years": required_years,
        "relevant_years": relevant_years,
        "total_years": total_years,
        "relevant_count": len(relevant),
        "reason": reason,
    }
    relevant.sort(key=lambda r: (r["skills"], r["months"] or 0), reverse=True)
    return _component("experience", weight, score, details), relevant


def score_role(candidate: CandidateFacts, job: JobFacts, weight: float) -> dict[str, Any]:
    titles = candidate.titles
    if not titles and not candidate.profile_text.strip():
        return _component("role", weight, None, {"method": None, "reason": "no_candidate_titles"})
    title_sim = title_similarity(titles, job.title)
    if candidate.embedding and job.embedding:
        raw = cosine(candidate.embedding, job.embedding)
        semantic = (raw - _EMBEDDING_FLOOR) / (_EMBEDDING_CEILING - _EMBEDDING_FLOOR)
        semantic = max(0.0, min(1.0, semantic))
        score = 0.6 * semantic + 0.4 * title_sim
        details = {"method": "embedding", "title_similarity": round(title_sim, 2), "semantic_similarity": round(semantic, 2)}
    else:
        text_sim = min(1.0, _tf_cosine(tokens(candidate.profile_text), tokens(job.text)) * 2.5)
        score = 0.6 * title_sim + 0.4 * text_sim
        details = {"method": "lexical", "title_similarity": round(title_sim, 2), "text_similarity": round(text_sim, 2)}
    return _component("role", weight, score, details)


def score_qualifications(candidate: CandidateFacts, job: JobFacts, weight: float) -> tuple[dict[str, Any], Status]:
    if not job.education_level or job.education_level == EducationLevel.NONE:
        return _component("qualifications", weight, None, {"reason": "no_job_requirement"}), "unknown"
    if candidate.education_level is None:
        return _component(
            "qualifications", weight, None, {"required": job.education_level.value, "reason": "no_candidate_education"}
        ), "unknown"
    ok = _EDUCATION_RANK[candidate.education_level] >= _EDUCATION_RANK[job.education_level]
    details = {"required": job.education_level.value, "candidate": candidate.education_level.value}
    return _component("qualifications", weight, 1.0 if ok else 0.3, details), "match" if ok else "mismatch"


def _preference_checks(candidate: CandidateFacts, job: JobFacts) -> list[dict[str, Any]]:
    prefs = candidate.preferences
    checks: list[dict[str, Any]] = []

    # Location / commute
    places = prefs.locations or ([candidate.city] if candidate.city else [])
    if job.remote_policy == RemotePolicy.REMOTE:
        checks.append({"key": "location", "status": "match", "reason": "remote_job"})
    elif places and job.city:
        distances = [d for d in (geo.distance_km(p, job.city) for p in places) if d is not None]
        if any(geo.same_place(p, job.city) for p in places):
            checks.append({"key": "location", "status": "match", "distance_km": 0})
        elif distances:
            nearest = min(distances)
            limit = prefs.max_commute_km or 50
            status: Status = "match" if nearest <= limit else ("partial" if nearest <= limit * 1.5 else "mismatch")
            checks.append({"key": "location", "status": status, "distance_km": nearest, "limit_km": limit})
        else:
            checks.append({"key": "location", "status": "unknown", "reason": "unknown_place"})
    else:
        checks.append({"key": "location", "status": "unknown", "reason": "no_location"})

    # Remote / hybrid / on-site
    if prefs.remote != RemotePreference.ANY:
        table: dict[tuple[str, str], Status] = {
            ("remote", "remote"): "match",
            ("remote", "hybrid"): "partial",
            ("remote", "onsite"): "mismatch",
            ("hybrid", "remote"): "match",
            ("hybrid", "hybrid"): "match",
            ("hybrid", "onsite"): "partial",
            ("onsite", "remote"): "partial",
            ("onsite", "hybrid"): "match",
            ("onsite", "onsite"): "match",
        }
        checks.append(
            {
                "key": "remote",
                "status": table[(prefs.remote.value, job.remote_policy.value)],
                "wanted": prefs.remote.value,
                "offered": job.remote_policy.value,
            }
        )

    if prefs.employment_types:
        ok = job.employment_type in prefs.employment_types
        checks.append({"key": "employment_type", "status": "match" if ok else "mismatch", "offered": job.employment_type})

    if prefs.salary_min_annual_eur:
        top = job.salary_annual_max_eur or job.salary_annual_min_eur
        if top is None:
            checks.append({"key": "salary", "status": "unknown", "reason": "no_salary_in_job"})
        else:
            status = (
                "match" if top >= prefs.salary_min_annual_eur else ("partial" if top >= prefs.salary_min_annual_eur * 0.9 else "mismatch")
            )
            checks.append({"key": "salary", "status": status, "job_annual_max_eur": top, "wanted_annual_eur": prefs.salary_min_annual_eur})

    if prefs.industries and job.industry:
        ok = job.industry.lower() in {i.lower() for i in prefs.industries}
        checks.append({"key": "industry", "status": "match" if ok else "partial", "offered": job.industry})
    return checks


def score_preferences(candidate: CandidateFacts, job: JobFacts, weight: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks = _preference_checks(candidate, job)
    values = {"match": 1.0, "partial": 0.5, "mismatch": 0.0}
    known = [values[c["status"]] for c in checks if c["status"] in values]
    score = sum(known) / len(known) if known else None
    return _component("preferences", weight, score, {"evaluated": len(known), "reason": None if known else "no_preferences"}), checks


def _eligibility(
    candidate: CandidateFacts, job: JobFacts, experience: dict[str, Any], education_status: Status, missing_required_count: int
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    for code in job.required_languages:
        level = candidate.languages.get(code)
        if level is None:
            (unknown if not candidate.languages else issues).append({"code": "language", "value": code})
        elif level not in _LANGUAGE_LEVEL_OK:
            issues.append({"code": "language_level", "value": code, "level": level})
    if education_status == "mismatch":
        issues.append({"code": "education", "value": job.education_level.value if job.education_level else None})
    elif job.education_level and job.education_level != EducationLevel.NONE and education_status == "unknown":
        unknown.append({"code": "education", "value": job.education_level.value})
    required_total = len(job.required_skills)
    if required_total and missing_required_count / required_total > 0.5:
        issues.append({"code": "required_skills", "missing": missing_required_count, "total": required_total})
    details = experience["details"]
    required = details.get("required_years")
    if required and experience["applicable"] and details["relevant_years"] < required * 0.5:
        issues.append({"code": "experience", "required_years": required, "relevant_years": details["relevant_years"]})
    elif required and not experience["applicable"]:
        unknown.append({"code": "experience", "required_years": required})
    status = "not_met" if issues else ("unknown" if unknown else "met")
    return {"status": status, "issues": issues, "unknown": unknown}


# ── public API ──────────────────────────────────────────────────────────────


def compute_match(candidate: CandidateFacts, job: JobFacts, weights: MatchingWeights, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    skills_component, skills = score_skills(candidate, job, weights.skills)
    experience_component, relevant_experience = score_experience(candidate, job, weights.experience, today)
    role_component = score_role(candidate, job, weights.role)
    qualifications_component, education_status = score_qualifications(candidate, job, weights.qualifications)
    preferences_component, preference_checks = score_preferences(candidate, job, weights.preferences)
    components = [skills_component, experience_component, role_component, qualifications_component, preferences_component]

    applicable = [c for c in components if c["applicable"]]
    total_weight = sum(c["weight"] for c in applicable)
    for c in components:
        c["effective_weight"] = round(c["weight"] / total_weight, 3) if c["applicable"] and total_weight else 0.0

    eligibility = _eligibility(candidate, job, experience_component, education_status, len(skills["missing_required"]))
    core_known = skills_component["applicable"] or role_component["applicable"]
    if len(applicable) < 2 or not core_known:
        score: int | None = None
        status = "insufficient_data"
    else:
        raw = sum(c["score"] * c["weight"] for c in applicable) / total_weight
        score = round(raw)
        status = "ok"
        if eligibility["status"] == "not_met":
            score = min(score, HARD_REQUIREMENT_CAP)

    strengths = sorted(
        (c for c in applicable if c["score"] is not None and c["score"] >= 70), key=lambda c: c["score"] * c["weight"], reverse=True
    )
    review = [c["key"] for c in components if not c["applicable"]]

    return {
        "score": score,
        "status": status,
        "components": components,
        "eligibility": eligibility,
        "capped": status == "ok" and eligibility["status"] == "not_met",
        "matching_skills": skills["matching"],
        "missing_required_skills": skills["missing_required"],
        "missing_preferred_skills": skills["missing_preferred"],
        "relevant_experience": relevant_experience[:5],
        "preference_checks": preference_checks,
        "strongest_factors": [c["key"] for c in strengths[:3]],
        "needs_review": review,
        "semantic_method": role_component["details"].get("method"),
        "algorithm_version": ALGORITHM_VERSION,
    }
