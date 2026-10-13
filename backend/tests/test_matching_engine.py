from datetime import date

from app.core.config import MatchingWeights
from app.models.enums import EducationLevel, ExperienceLevel, RemotePolicy, RemotePreference, SalaryPeriod
from app.services.matching.engine import HARD_REQUIREMENT_CAP, CandidateFacts, ExperienceFact, JobFacts, PreferenceFacts, compute_match
from app.utils.salary import to_annual_eur
from app.utils.skills import normalize_skill, text_mentions_skill

TODAY = date(2026, 10, 1)
W = MatchingWeights()


def candidate(**kw) -> CandidateFacts:
    base = dict(
        skills={"python": "Python", "postgresql": "PostgreSQL", "docker": "Docker"},
        experiences=[ExperienceFact("e1", "Backend Developer", "Acme", "REST API's in Python, PostgreSQL", "2021-01", None, True)],
        titles=["Backend Developer"],
        profile_text="Backend developer Python PostgreSQL API",
        education_level=EducationLevel.BACHELOR,
        languages={"nl": "native", "en": "fluent"},
        preferences=PreferenceFacts(locations=["Gent"], max_commute_km=40, remote=RemotePreference.HYBRID),
        city="Gent",
    )
    base.update(kw)
    return CandidateFacts(**base)  # type: ignore[arg-type]


def job(**kw) -> JobFacts:
    base = dict(
        id="j1",
        title="Backend Developer",
        text="Backend developer Python PostgreSQL API",
        required_skills={"python": "Python", "postgresql": "PostgreSQL"},
        preferred_skills={"kubernetes": "Kubernetes"},
        min_years=3,
        experience_level=ExperienceLevel.MEDIOR,
        education_level=EducationLevel.BACHELOR,
        required_languages=["nl"],
        city="Gent",
        remote_policy=RemotePolicy.HYBRID,
        employment_type="full_time",
        salary_annual_min_eur=None,
        salary_annual_max_eur=None,
        industry=None,
    )
    base.update(kw)
    return JobFacts(**base)  # type: ignore[arg-type]


def test_strong_match_scores_high_with_breakdown():
    result = compute_match(candidate(), job(), W, TODAY)
    assert result["status"] == "ok"
    assert result["score"] >= 80
    assert {s["name"] for s in result["matching_skills"]} == {"Python", "PostgreSQL"}
    assert [s["name"] for s in result["missing_preferred_skills"]] == ["Kubernetes"]
    assert result["eligibility"]["status"] == "met"
    keys = {c["key"] for c in result["components"]}
    assert keys == {"skills", "experience", "role", "qualifications", "preferences"}
    assert abs(sum(c["effective_weight"] for c in result["components"]) - 1) < 0.01


def test_missing_data_is_not_applicable_and_weights_renormalize():
    result = compute_match(candidate(education_level=None, preferences=PreferenceFacts(), city=None), job(), W, TODAY)
    quals = next(c for c in result["components"] if c["key"] == "qualifications")
    assert quals["applicable"] is False and quals["effective_weight"] == 0
    assert "qualifications" in result["needs_review"]
    assert result["eligibility"]["status"] == "unknown"
    assert result["score"] is not None


def test_empty_profile_gives_no_score_instead_of_a_fake_one():
    empty = candidate(
        skills={}, experiences=[], titles=[], profile_text="", education_level=None, languages={}, preferences=PreferenceFacts(), city=None
    )
    result = compute_match(empty, job(), W, TODAY)
    assert result["score"] is None
    assert result["status"] == "insufficient_data"


def test_hard_requirement_caps_score_even_with_high_similarity():
    result = compute_match(candidate(), job(required_languages=["nl", "fr"]), W, TODAY)
    assert result["eligibility"]["status"] == "not_met"
    assert {"code": "language", "value": "fr"} in result["eligibility"]["issues"]
    assert result["score"] <= HARD_REQUIREMENT_CAP
    assert result["capped"] is True


def test_most_required_skills_missing_is_a_hard_issue():
    result = compute_match(candidate(), job(required_skills={"java": "Java", "spring boot": "Spring Boot", "python": "Python"}), W, TODAY)
    assert any(i["code"] == "required_skills" for i in result["eligibility"]["issues"])
    assert result["score"] <= HARD_REQUIREMENT_CAP


def test_experience_overlaps_are_counted_once():
    exps = [
        ExperienceFact("a", "Backend Developer", "A", "Python", "2020-01", "2021-12", False),
        ExperienceFact("b", "Backend Developer", "B", "Python", "2021-01", "2021-12", False),
    ]
    result = compute_match(candidate(experiences=exps), job(min_years=4), W, TODAY)
    details = next(c for c in result["components"] if c["key"] == "experience")["details"]
    assert details["relevant_years"] == 2.0


def test_preferences_location_remote_and_salary():
    prefs = PreferenceFacts(locations=["Gent"], max_commute_km=30, remote=RemotePreference.REMOTE, salary_min_annual_eur=60000)
    result = compute_match(
        candidate(preferences=prefs), job(city="Liège", remote_policy=RemotePolicy.ONSITE, salary_annual_max_eur=50000), W, TODAY
    )
    checks = {c["key"]: c["status"] for c in result["preference_checks"]}
    assert checks == {"location": "mismatch", "remote": "mismatch", "salary": "mismatch"}
    remote_job = compute_match(candidate(preferences=prefs), job(city="Liège", remote_policy=RemotePolicy.REMOTE), W, TODAY)
    assert {c["key"]: c["status"] for c in remote_job["preference_checks"]}["location"] == "match"


def test_salary_is_normalized_before_comparison():
    assert to_annual_eur(4000, SalaryPeriod.MONTH) == round(4000 * 13.92)
    assert to_annual_eur(55000, SalaryPeriod.YEAR) == 55000
    assert to_annual_eur(30, SalaryPeriod.HOUR) == 30 * 38 * 52
    assert to_annual_eur(4000, SalaryPeriod.MONTH, "USD") is None


def test_skill_synonyms():
    assert normalize_skill("JS") == normalize_skill("javascript") == "javascript"
    assert normalize_skill(".NET Core") == "dotnet"
    assert text_mentions_skill("Built services in Node.js and C#", "nodejs")
    assert text_mentions_skill("Built services in Node.js and C#", "csharp")
    assert not text_mentions_skill("Javascript developer", "java")


def test_skill_evidenced_only_in_experience_counts():
    result = compute_match(candidate(skills={}), job(), W, TODAY)
    evidence = {s["name"]: s["evidence"] for s in result["matching_skills"]}
    assert evidence["Python"] == "experience"


def test_grouped_skill_entries_are_matched():
    from app.utils.skills import split_skills

    grouped = ["Angular, Vue.js, React, .NET MAUI, SPFX", "SCRUM, Atlassian Jira & Confluence", "SAP BTP Training - Basics to Advanced"]
    assert {"React", "Vue.js", "Atlassian Jira", "Confluence"} <= set(split_skills(grouped))
    skills = {normalize_skill(s): s for s in split_skills(grouped)}
    result = compute_match(
        candidate(skills=skills, skills_text=" | ".join(grouped)),
        job(required_skills={"react": "React", "sap btp": "SAP BTP"}, preferred_skills={}),
        W,
        TODAY,
    )
    assert {s["name"] for s in result["matching_skills"]} == {"React", "SAP BTP"}


def test_internships_do_not_count_as_work_experience():
    exps = [
        ExperienceFact("i", "Backend Developer", "Acme (Internship)", "Python", "2024-09", "2025-05", False, is_internship=True),
        ExperienceFact("j", "Backend Developer", "Globex", "Python", "2025-09", "2025-10", False),
    ]
    result = compute_match(candidate(experiences=exps), job(min_years=1), W, TODAY)
    details = next(c for c in result["components"] if c["key"] == "experience")["details"]
    assert details["relevant_months"] == 2  # only Sep + Oct 2025
    assert details["internship_months"] == 9
    assert any(i["code"] == "experience" for i in result["eligibility"]["issues"])
    assert any(r["internship"] for r in result["relevant_experience"])


def test_experience_is_counted_in_months_and_year_only_dates_are_not_inflated():
    exact = compute_match(
        candidate(experiences=[ExperienceFact("a", "Backend Developer", "A", "Python", "2025-03", "2025-08", False)]),
        job(min_years=1),
        W,
        TODAY,
    )
    details = next(c for c in exact["components"] if c["key"] == "experience")["details"]
    assert details["relevant_months"] == 6
    assert next(c for c in exact["components"] if c["key"] == "experience")["score"] == 50

    vague = compute_match(
        candidate(experiences=[ExperienceFact("b", "Backend Developer", "B", "Python", "2024", "2025", False)]), job(min_years=2), W, TODAY
    )
    vague_details = next(c for c in vague["components"] if c["key"] == "experience")["details"]
    assert vague_details["relevant_months"] == 12  # not 24
    assert vague_details["estimated_dates"] is True


def test_cv_dates_with_month_names_are_parsed():
    from app.services.cv.llm_schema import _ym, is_present

    assert _ym("Sep 2024") == "2024-09"
    assert _ym("september 2024") == "2024-09"
    assert _ym("mrt. 2021") == "2021-03"
    assert _ym("févr. 2020") == "2020-02"
    assert _ym("03/2021") == "2021-03"
    assert _ym("2019") == "2019"
    assert is_present("heden") and is_present("Present") and not is_present("May 2025")
