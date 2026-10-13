from tests.conftest import create_job, fill_profile, register, verify


def _cv_version(candidate) -> str:
    return candidate.post("/cv-versions", {"title": "Mijn cv"}).json()["id"]


def test_platform_application_flow(employer, candidate):
    job = create_job(employer)
    fill_profile(candidate)
    version_id = _cv_version(candidate)

    no_consent = candidate.post("/applications", {"job_id": job["id"], "channel": "platform", "cv_version_id": version_id})
    assert no_consent.status_code == 422 and no_consent.json()["error"]["code"] == "consent_required"
    no_cv = candidate.post("/applications", {"job_id": job["id"], "channel": "platform", "share_consent": True})
    assert no_cv.status_code == 422

    created = candidate.post(
        "/applications",
        {"job_id": job["id"], "channel": "platform", "cv_version_id": version_id, "share_consent": True, "cover_letter": "Beste,"},
    )
    assert created.status_code == 201, created.text
    app_id = created.json()["id"]
    assert created.json()["status"] == "applied"
    duplicate = candidate.post("/applications", {"job_id": job["id"], "channel": "external"})
    assert duplicate.status_code == 409

    # The employer sees the application and the shared CV, and gets a notification.
    applicants = employer.get("/employer/applications").json()
    assert [a["id"] for a in applicants] == [app_id]
    detail = employer.get(f"/employer/applications/{app_id}").json()
    assert detail["cv"]["contact"]["full_name"] == "Kandidaat Een"
    assert "Python" in detail["matching_skills"]
    assert employer.client.get(f"/api/v1/employer/applications/{app_id}/cv").content.startswith(b"%PDF")
    assert employer.get("/notifications/unread-count").json()["count"] == 1

    # Status updates by the employer are recorded and notify the candidate.
    assert employer.patch(f"/employer/applications/{app_id}", {"status": "interview", "note": "Gesprek op dinsdag"}).status_code == 200
    mine = candidate.get(f"/applications/{app_id}").json()
    assert mine["status"] == "interview"
    assert [h["to_status"] for h in mine["history"]] == ["applied", "interview"]
    assert candidate.get("/notifications/unread-count").json()["count"] == 1

    # Candidates can't set employer statuses on platform applications, but can withdraw.
    assert candidate.patch(f"/applications/{app_id}", {"status": "offer"}).status_code == 403
    assert candidate.patch(f"/applications/{app_id}", {"status": "withdrawn"}).json()["status"] == "withdrawn"
    assert employer.patch(f"/employer/applications/{app_id}", {"status": "offer"}).status_code == 409


def test_other_companies_cannot_see_applicants(employer, candidate, db):
    job = create_job(employer)
    fill_profile(candidate)
    app_id = candidate.post(
        "/applications", {"job_id": job["id"], "channel": "platform", "cv_version_id": _cv_version(candidate), "share_consent": True}
    ).json()["id"]
    other = register("employer", company="Ander BV")
    verify(db, other.user["email"])
    assert other.get("/employer/applications").json() == []
    assert other.get(f"/employer/applications/{app_id}").status_code == 404
    assert other.patch(f"/employer/applications/{app_id}", {"status": "rejected"}).status_code == 404
    assert other.client.get(f"/api/v1/employer/applications/{app_id}/cv").status_code == 404
    assert candidate.get("/employer/applications").status_code == 403


def test_external_tracking_never_auto_confirms(employer, candidate):
    job = create_job(employer, application_url="https://example.com/jobs/1")
    tracked = candidate.post("/applications", {"job_id": job["id"], "channel": "external", "status": "saved", "notes": "Nog bellen"}).json()
    assert tracked["status"] == "saved" and tracked["applied_at"] is None
    updated = candidate.patch(f"/applications/{tracked['id']}", {"status": "applied"}).json()
    assert updated["status"] == "applied" and updated["applied_at"]
    assert employer.get("/employer/applications").json() == []  # external tracking is private to the candidate


def test_cannot_attach_someone_elses_cv(employer, candidate):
    job = create_job(employer)
    other = register()
    fill_profile(other)
    foreign = _cv_version(other)
    response = candidate.post(
        "/applications", {"job_id": job["id"], "channel": "platform", "cv_version_id": foreign, "share_consent": True}
    )
    assert response.status_code == 404
