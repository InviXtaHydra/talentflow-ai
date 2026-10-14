from tests.conftest import JOB, company_id, create_job, fill_profile, register


def test_unverified_employer_cannot_publish():
    api = register("employer", company="Onbevestigd BV")
    response = api.post(f"/companies/{company_id(api)}/jobs", JOB)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "email_not_verified"
    assert api.post(f"/companies/{company_id(api)}/jobs", {**JOB, "status": "draft"}).status_code == 201


def test_employer_publishes_and_candidate_finds_and_matches(employer, candidate):
    job = create_job(employer)
    assert job["status"] == "published" and job["can_edit"] is True
    fill_profile(candidate)

    page = candidate.get("/jobs", params={"q": "python"}).json()
    assert page["total"] == 1
    found = page["items"][0]
    assert found["id"] == job["id"]
    assert found["match"]["score"] is not None
    assert "Python" in found["match"]["matching_skills"]

    match = candidate.get(f"/jobs/{job['id']}/match").json()
    assert match["algorithm_version"]
    assert match["result"]["components"]

    assert candidate.get("/jobs", params={"remote": "remote"}).json()["total"] == 0
    assert candidate.get("/jobs", params={"skills": "sql"}).json()["total"] == 1
    assert candidate.get("/jobs", params={"salary_min_annual": 70000}).json()["total"] == 0
    assert candidate.get("/jobs", params={"salary_min_annual": 50000}).json()["total"] == 1


def test_match_is_recalculated_when_profile_changes(employer, candidate):
    job = create_job(employer)
    before = candidate.get(f"/jobs/{job['id']}/match").json()
    assert before["score"] is None  # empty profile: no score instead of a guess
    fill_profile(candidate)
    after = candidate.get(f"/jobs/{job['id']}/match").json()
    assert after["score"] is not None


def test_drafts_are_private_and_companies_are_isolated(employer, db):
    from tests.conftest import verify

    draft = create_job(employer, status="draft")
    other = register("employer", company="Concurrent NV")
    verify(db, other.user["email"])
    anonymous = register("candidate")
    assert anonymous.get(f"/jobs/{draft['id']}").status_code == 404
    assert other.get(f"/jobs/{draft['id']}").status_code == 404
    assert other.patch(f"/jobs/{draft['id']}", {"title": "Overgenomen"}).status_code == 403
    assert other.post(f"/companies/{company_id(employer)}/jobs", JOB).status_code == 403
    assert anonymous.post(f"/companies/{company_id(employer)}/jobs", JOB).status_code == 403
    assert employer.patch(f"/jobs/{draft['id']}", {"status": "published"}).json()["status"] == "published"


def test_close_job_and_validation(employer):
    job = create_job(employer)
    assert employer.patch(f"/jobs/{job['id']}", {"status": "closed"}).json()["status"] == "closed"
    assert employer.post(f"/companies/{company_id(employer)}/jobs", {**JOB, "salary_min": 5000, "salary_max": 4000}).status_code == 422
    assert employer.post(f"/companies/{company_id(employer)}/jobs", {**JOB, "application_url": "javascript:alert(1)"}).status_code == 422


def test_saved_jobs(employer, candidate):
    job = create_job(employer)
    assert candidate.post(f"/jobs/{job['id']}/save").status_code == 200
    assert candidate.post(f"/jobs/{job['id']}/save").status_code == 200  # idempotent
    saved = candidate.get("/jobs/saved").json()
    assert [j["id"] for j in saved] == [job["id"]]
    assert candidate.get(f"/jobs/{job['id']}").json()["saved"] is True
    candidate.delete(f"/jobs/{job['id']}/save")
    assert candidate.get("/jobs/saved").json() == []
    assert employer.post(f"/jobs/{job['id']}/save").status_code == 403  # candidates only


def test_company_members_owner_only(employer, db):
    from tests.conftest import verify

    colleague = register("employer", email="collega@example.com")
    verify(db, "collega@example.com")
    cid = company_id(employer)
    assert employer.post(f"/companies/{cid}/members", {"email": "collega@example.com", "role": "recruiter"}).status_code == 201
    assert colleague.get(f"/companies/{cid}/members").status_code == 200
    assert colleague.post(f"/companies/{cid}/members", {"email": "x@example.com"}).status_code == 403  # recruiters can't manage members


def test_job_detail_shows_offer_team_process_and_activity(employer, candidate):
    job = create_job(
        employer,
        benefits=["Maaltijdcheques", "Opleidingsbudget"],
        about_team="Een team van zes developers.",
        hiring_process=["Kennismaking", "Technisch gesprek", "Voorstel"],
        department="Engineering",
        hours_per_week=38,
        contract_duration_months=12,
        start_date="2026-12-01",
        openings=2,
    )
    assert job["benefits"] == ["Maaltijdcheques", "Opleidingsbudget"]
    assert job["hiring_process"][1] == "Technisch gesprek"
    assert (job["department"], job["hours_per_week"], job["contract_duration_months"], job["openings"]) == ("Engineering", 38, 12, 2)
    assert job["start_date"] == "2026-12-01"
    assert job["company_profile"]["open_jobs"] == 1
    assert job["recruiter"]["full_name"] == employer.user["full_name"]
    assert job["applicant_count"] == 0

    # A bookmark in the tracker is not an application; an actual application is, and a candidate view is counted.
    candidate.post("/applications", {"job_id": job["id"], "channel": "external", "status": "saved"})
    seen = candidate.get(f"/jobs/{job['id']}").json()
    assert seen["applicant_count"] == 0
    assert seen["view_count"] == 1
    other = register("candidate")
    assert other.post("/applications", {"job_id": job["id"], "channel": "external", "status": "applied"}).status_code == 201
    assert candidate.get(f"/jobs/{job['id']}").json()["applicant_count"] == 1

    updated = employer.patch(f"/jobs/{job['id']}", {"benefits": [], "openings": None, "hours_per_week": None}).json()
    assert updated["benefits"] == [] and updated["openings"] == 1 and updated["hours_per_week"] is None
