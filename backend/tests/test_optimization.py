import copy
import io

from docx import Document
from pypdf import PdfReader

from app.integrations.ai import factory
from app.schemas.cv import OptimizerOutput
from tests.conftest import create_job, fill_profile, register, run_tasks


def _output(**overrides) -> OptimizerOutput:
    data = {
        "headline": "Python backend developer",
        "summary": "Backend developer met drie jaar ervaring in Python en SQL, gericht op API's en datapijplijnen.",
        "experience_order": ["exp-aaaa0001", "exp-aaaa0002", "exp-does-not-exist"],
        "experiences": [
            {
                "source_id": "exp-aaaa0001",
                "bullets": [
                    {"text": "Ontwikkelde REST API's in Python voor 3 interne teams", "source_refs": ["exp-aaaa0001"]},
                    {"text": "Verhoogde de omzet met 40% door slimme API's", "source_refs": ["exp-aaaa0001"]},  # invented number
                    {"text": "Beheerde Kubernetes-clusters in productie", "source_refs": ["exp-aaaa0001"]},  # invented skill
                ],
            }
        ],
        "skills": ["SQL", "Python", "Kubernetes", "Docker"],
        "emphasized_keywords": ["Python", "SQL"],
        "changes": [
            {"section": "Samenvatting", "description": "Samenvatting gericht op Python-development"},
            {"section": "Werkervaring", "description": "Alles herschreven met Kubernetes"},
        ],
        "questions": [{"question": "Hoeveel API-calls per dag verwerkten je API's?", "reason": "Kwantificeren"}],
        "summary_source_refs": ["exp-aaaa0001"],
        "project_order": [],
        "projects": [],
    }
    data.update(overrides)
    return OptimizerOutput.model_validate(data)


def _optimize(candidate, job_id: str, fake_ai, output: OptimizerOutput | None = None) -> dict:
    fake_ai.structured[OptimizerOutput] = lambda system, user: output or _output()
    started = candidate.post(f"/jobs/{job_id}/optimize-cv", {"language": "nl", "template": "modern"})
    assert started.status_code == 202, started.text
    assert started.json()["status"] == "generating"
    run_tasks()
    return candidate.get(f"/cv-optimizations/{started.json()['optimization_id']}").json()


def test_optimization_end_to_end_with_fact_check(employer, candidate, fake_ai):
    job = create_job(employer)
    fill_profile(candidate)
    result = _optimize(candidate, job["id"], fake_ai)

    assert result["status"] == "ready"
    content = result["content"]
    # Hard facts come from the source profile.
    assert [e["employer"] for e in content["experiences"]] == ["Acme", "Globex"]
    assert content["experiences"][0]["start"] == "2022-01"
    assert content["contact"]["full_name"] == "Kandidaat Een"
    assert content["education"][0]["institution"] == "HOGENT"
    # Supported rewrite kept; invented number and invented skill moved to review.
    bullets = [b["text"] for b in content["experiences"][0]["bullets"]]
    assert "Ontwikkelde REST API's in Python voor 3 interne teams" in bullets
    assert not any("40%" in b or "Kubernetes" in b for b in bullets)
    review = result["optimization"]["review_items"]
    reasons = " ".join(r["reason"] for r in review)
    assert "40" in reasons and "kubernetes" in reasons.lower()
    assert "Kubernetes" not in content["skills"]
    assert content["skills"][:2] == ["SQL", "Python"]
    # Change notes describe what actually changed; the model's claim about Kubernetes rewrites is dropped.
    notes = " ".join(c["description"] for c in result["optimization"]["changes"])
    assert "Kubernetes" not in notes
    # Same engine before and after; a rewrite doesn't add qualifications.
    assert result["match_before"]["algorithm_version"] == result["match_after"]["algorithm_version"]
    assert result["score_before"] is not None and result["score_after"] is not None
    assert result["original_content"]["experiences"][0]["bullets"][0]["text"] == "Bouwde REST API's in Python voor 3 interne teams"
    assert result["optimization"]["questions"]
    # The profile itself is untouched.
    assert (
        candidate.get("/candidates/me").json()["content"]["experiences"][0]["bullets"][0]
        == "Bouwde REST API's in Python voor 3 interne teams"
    )


def test_edit_restore_export_and_versions_persist(employer, candidate, fake_ai):
    job = create_job(employer)
    fill_profile(candidate)
    opt = _optimize(candidate, job["id"], fake_ai)
    oid = opt["id"]

    edited = copy.deepcopy(opt["content"])
    edited["summary"] = "Mijn eigen aangepaste samenvatting."
    response = candidate.patch(f"/cv-optimizations/{oid}", {"content": edited, "template": "technical"})
    assert response.status_code == 200
    reloaded = candidate.get(f"/cv-optimizations/{oid}").json()
    assert reloaded["content"]["summary"] == "Mijn eigen aangepaste samenvatting."
    assert reloaded["template"] == "technical" and reloaded["user_edited_at"]
    assert reloaded["generated_content"]["summary"] != "Mijn eigen aangepaste samenvatting."

    pdf = candidate.post(f"/cv-optimizations/{oid}/export", {"format": "pdf"})
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert "attachment" in pdf.headers["content-disposition"]
    assert str(oid) not in pdf.headers["content-disposition"]
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Mijn eigen aangepaste samenvatting." in text and "Acme" in text

    docx = candidate.post(f"/cv-optimizations/{oid}/export", {"format": "docx", "template": "minimal"})
    assert docx.status_code == 200
    doc_text = "\n".join(p.text for p in Document(io.BytesIO(docx.content)).paragraphs)
    assert "Mijn eigen aangepaste samenvatting." in doc_text and "HOGENT" in doc_text

    restored = candidate.post(f"/cv-optimizations/{oid}/restore", {"target": "generated"}).json()
    assert restored["content"]["summary"] == opt["content"]["summary"]
    original = candidate.post(f"/cv-optimizations/{oid}/restore", {"target": "original"}).json()
    assert original["content"]["summary"] == original["original_content"]["summary"]

    versions = candidate.get("/cv-versions").json()
    assert any(v["id"] == oid and v["last_exported_at"] for v in versions)
    assert candidate.delete(f"/cv-versions/{oid}").status_code == 200
    assert candidate.get(f"/cv-optimizations/{oid}").status_code == 404


def test_optimizations_are_private(employer, candidate, fake_ai):
    job = create_job(employer)
    fill_profile(candidate)
    oid = _optimize(candidate, job["id"], fake_ai)["id"]
    other = register()
    assert other.get(f"/cv-optimizations/{oid}").status_code == 404
    assert other.post(f"/cv-optimizations/{oid}/export", {"format": "pdf"}).status_code == 404
    assert other.patch(f"/cv-optimizations/{oid}", {"title": "x"}).status_code == 404
    assert employer.get(f"/cv-optimizations/{oid}").status_code == 403


def test_double_click_does_not_start_two_optimizations(employer, candidate, fake_ai):
    job = create_job(employer)
    fill_profile(candidate)
    fake_ai.structured[OptimizerOutput] = lambda s, u: _output()
    first = candidate.post(f"/jobs/{job['id']}/optimize-cv", {"language": "nl"}).json()
    second = candidate.post(f"/jobs/{job['id']}/optimize-cv", {"language": "nl"}).json()
    assert first["optimization_id"] == second["optimization_id"]
    assert first["task_id"] == second["task_id"]


def test_model_failure_marks_version_failed_after_retries(employer, candidate, fake_ai, db):
    from app.models.entities import BackgroundTask

    job = create_job(employer)
    fill_profile(candidate)
    fake_ai.unavailable = True
    oid = candidate.post(f"/jobs/{job['id']}/optimize-cv", {}).json()["optimization_id"]
    run_tasks()
    # The retry is scheduled with a backoff; make it due and run it.
    db.query(BackgroundTask).update({"run_after": BackgroundTask.created_at})
    db.commit()
    run_tasks()
    result = candidate.get(f"/cv-optimizations/{oid}").json()
    assert result["status"] == "failed"
    assert "Ollama" in result["error_message"] or "AI" in result["error_message"]


def test_without_ai_real_profiles_get_a_clear_error(employer, candidate, monkeypatch):
    job = create_job(employer)
    fill_profile(candidate)
    monkeypatch.setattr(factory, "_build_llm", lambda: None)
    response = candidate.post(f"/jobs/{job['id']}/optimize-cv", {})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_not_configured"
    assert "AI_PROVIDER" in response.json()["error"]["message"]


def test_without_ai_demo_records_get_a_labelled_simulation(db, monkeypatch):
    from app.seed.seed import DEMO_CANDIDATE_EMAIL, run
    from tests.conftest import Api

    run(db, "demo-password-123")
    monkeypatch.setattr(factory, "_build_llm", lambda: None)
    api = Api()
    assert api.post("/auth/login", {"email": DEMO_CANDIDATE_EMAIL, "password": "demo-password-123"}).status_code == 200
    job_id = api.get("/jobs", params={"q": "Data Engineer"}).json()["items"][0]["id"]
    started = api.post(f"/jobs/{job_id}/optimize-cv", {})
    assert started.status_code == 202
    run_tasks(100)
    result = api.get(f"/cv-optimizations/{started.json()['optimization_id']}").json()
    assert result["status"] == "ready"
    assert result["is_simulated"] is True
    assert result["provider"] == "demo"
