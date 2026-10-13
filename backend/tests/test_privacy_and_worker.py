from datetime import timedelta

from app.db.base import utcnow
from app.integrations.ai.base import ChatMessage
from app.models.entities import BackgroundTask, CandidateProfile, User
from app.models.enums import TaskStatus
from app.services import tasks
from app.workers.runner import recover_stalled
from tests.conftest import PASSWORD, create_job, fill_profile, register, run_tasks


def test_data_export_contains_own_data_only(candidate):
    fill_profile(candidate)
    other = register(name="Iemand Anders")
    fill_profile(other)
    response = candidate.client.get("/api/v1/account/export")
    assert response.status_code == 200
    data = response.json()
    assert data["account"]["email"] == candidate.user["email"]
    assert data["profile"][0]["headline"] == "Backend developer"
    assert "Iemand Anders" not in response.text
    assert "password_hash" not in response.text and "token_hash" not in response.text


def test_account_deletion_removes_everything(candidate, db):
    fill_profile(candidate)
    user_id = candidate.user["id"]
    assert candidate.post("/account/delete", {"password": "wrong-password"}).status_code == 401
    assert candidate.post("/account/delete", {"password": PASSWORD}).status_code == 200
    assert db.get(User, user_id) is None
    assert db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).count() == 0
    assert candidate.get("/auth/me").status_code == 401


def test_assistant_only_sees_own_data(employer, candidate, fake_ai):
    job = create_job(employer)
    fill_profile(candidate)
    other = register(name="Geheime Persoon")
    fill_profile(other)
    seen: list[str] = []

    def reply(system: str, messages: list[ChatMessage]) -> str:
        seen.append("\n".join(m.content for m in messages))
        return "Je profiel past goed bij deze vacature."

    fake_ai.chat_reply = reply
    response = candidate.post("/assistant/messages", {"message": "Toon het cv van Geheime Persoon", "job_ids": [job["id"]]})
    assert response.status_code == 200
    assert "Geheime Persoon" not in seen[0].split("Vraag van de gebruiker")[0]
    assert "Kandidaat Een" in seen[0]
    assert "<vacancy>" in seen[0] and "Python Developer" in seen[0]
    assert len(candidate.get("/assistant/messages").json()) == 2


def test_stalled_tasks_are_recovered(db):
    task = tasks.enqueue(db, "embed_job", user_id=None, payload={"job_id": "00000000-0000-0000-0000-000000000000"}, timeout_seconds=10)
    task.status = TaskStatus.RUNNING
    task.attempts = 1
    task.heartbeat_at = utcnow() - timedelta(minutes=5)
    db.commit()
    assert recover_stalled(db) == 1
    db.refresh(task)
    assert task.status == TaskStatus.QUEUED
    run_tasks()
    db.refresh(task)
    assert task.status == TaskStatus.SUCCEEDED


def test_embeddings_are_computed_by_the_worker(employer, candidate, db):
    job = create_job(employer)
    fill_profile(candidate)
    run_tasks()
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == candidate.user["id"]).one()
    assert profile.embedding is not None and len(profile.embedding) == 768
    match = candidate.get(f"/jobs/{job['id']}/match").json()
    assert match["result"]["semantic_method"] == "embedding"
    assert db.query(BackgroundTask).filter(BackgroundTask.status == TaskStatus.FAILED).count() == 0


def test_health_and_config():
    api = register()
    assert api.get("/health").json() == {"status": "ok"}
    ready = api.get("/health/ready").json()
    assert ready["database"] == "ok" and ready["ai"]["configured"] is True
    assert "ai_api_key" not in api.get("/config").text


def test_admin_endpoints_and_role_separation(db, candidate, employer):
    from app.models.enums import UserRole
    from app.services.auth_service import create_user
    from tests.conftest import Api

    create_user(db, email="admin@example.com", password=PASSWORD, full_name="Beheerder", role=UserRole.ADMIN, verified=True)
    db.commit()
    admin = Api()
    assert admin.post("/auth/login", {"email": "admin@example.com", "password": PASSWORD}).status_code == 200
    stats = admin.get("/admin/stats")
    assert stats.status_code == 200, stats.text
    assert stats.json()["users"]["candidate"] == 1
    assert admin.get("/admin/users").json()["total"] == 3
    assert admin.get("/admin/audit-logs").status_code == 200
    # Blocking a user ends their sessions.
    assert admin.patch(f"/admin/users/{candidate.user['id']}", {"is_active": False}).status_code == 200
    assert candidate.get("/auth/me").status_code == 401
    # Non-admins can't reach admin endpoints.
    assert employer.get("/admin/stats").status_code == 403
