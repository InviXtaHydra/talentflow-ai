"""Test setup: a separate PostgreSQL database (talentflow_test), migrated with Alembic, the fake AI provider,
an in-memory e-mail outbox and a temporary storage directory. No external service is called."""

import os
import tempfile

TEST_DB = "talentflow_test"
_base_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://talentflow:talentflow@db:5432/talentflow")
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": _base_url.rsplit("/", 1)[0] + f"/{TEST_DB}",
        "AI_PROVIDER": "fake",
        "EMBEDDING_PROVIDER": "fake",
        "EMAIL_BACKEND": "memory",
        "STORAGE_DIR": tempfile.mkdtemp(prefix="talentflow-test-"),
        "SECRET_KEY": "test-secret-key-that-is-long-enough",
        "FRONTEND_URL": "http://testserver",
    }
)

import uuid  # noqa: E402
from collections.abc import Iterator  # noqa: E402
from typing import Any  # noqa: E402

import psycopg  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.rate_limit import rate_limiter  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.integrations.ai.factory import get_llm, reset_providers  # noqa: E402
from app.integrations.email.sender import outbox  # noqa: E402
from app.main import app  # noqa: E402
from app.models.entities import User  # noqa: E402
from app.workers.runner import run_once  # noqa: E402


def _create_database() -> None:
    admin_url = _base_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,)).fetchone()
        if exists:
            conn.execute(f'DROP DATABASE "{TEST_DB}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{TEST_DB}"')


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    _create_database()
    config = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    config.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(config, "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_state() -> Iterator[None]:
    yield
    tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    rate_limiter.reset()
    outbox.clear()
    reset_providers()


@pytest.fixture
def fake_ai():
    return get_llm()


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


class Api:
    """TestClient wrapper that handles the CSRF double-submit token like the frontend does."""

    def __init__(self) -> None:
        self.client = TestClient(app)
        self.client.get("/api/v1/auth/csrf")

    def _headers(self) -> dict[str, str]:
        return {"X-CSRF-Token": self.client.cookies.get("tf_csrf", "")}

    def get(self, path: str, **kw: Any):
        return self.client.get(f"/api/v1{path}", **kw)

    def post(self, path: str, json: Any = None, **kw: Any):
        return self.client.post(f"/api/v1{path}", json=json, headers=self._headers(), **kw)

    def patch(self, path: str, json: Any = None):
        return self.client.patch(f"/api/v1{path}", json=json, headers=self._headers())

    def put(self, path: str, json: Any = None):
        return self.client.put(f"/api/v1{path}", json=json, headers=self._headers())

    def delete(self, path: str):
        return self.client.delete(f"/api/v1{path}", headers=self._headers())


PASSWORD = "correct-horse-battery"


def register(account_type: str = "candidate", email: str | None = None, company: str | None = None, name: str = "Test Gebruiker") -> Api:
    api = Api()
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    response = api.post(
        "/auth/register",
        {
            "email": email,
            "password": PASSWORD,
            "full_name": name,
            "account_type": account_type,
            "company_name": company,
            "accept_terms": True,
        },
    )
    assert response.status_code == 201, response.text
    api.user = response.json()  # type: ignore[attr-defined]
    return api


def verify(db_session, email: str) -> None:
    from app.db.base import utcnow

    user = db_session.query(User).filter(User.email == email).one()
    user.email_verified_at = utcnow()
    db_session.commit()


def run_tasks(limit: int = 20) -> int:
    count = 0
    while count < limit and run_once():
        count += 1
    return count


@pytest.fixture
def candidate() -> Api:
    return register("candidate", name="Kandidaat Een")


@pytest.fixture
def employer(db) -> Api:
    api = register("employer", company="Testbedrijf", name="Werkgever Een")
    verify(db, api.user["email"])  # type: ignore[attr-defined]
    return api


PROFILE = {
    "headline": "Backend developer",
    "summary": "Developer met drie jaar ervaring in Python en SQL. Ik bouw API's en datapijplijnen voor interne teams.",
    "city": "Gent",
    "phone": "+32 470 11 22 33",
    "content": {
        "experiences": [
            {
                "id": "exp-aaaa0001",
                "title": "Backend Developer",
                "employer": "Acme",
                "start": "2022-01",
                "end": None,
                "is_current": True,
                "bullets": ["Bouwde REST API's in Python voor 3 interne teams", "Onderhield PostgreSQL-databanken"],
            },
            {
                "id": "exp-aaaa0002",
                "title": "Support Engineer",
                "employer": "Globex",
                "start": "2020-01",
                "end": "2021-12",
                "bullets": ["Hielp klanten met technische vragen"],
            },
        ],
        "education": [
            {
                "id": "edu-aaaa0001",
                "degree": "Bachelor Toegepaste Informatica",
                "institution": "HOGENT",
                "level": "professional_bachelor",
                "start": "2017",
                "end": "2020",
            }
        ],
        "skills": ["Python", "SQL", "PostgreSQL", "Docker", "Git"],
        "languages": [{"code": "nl", "level": "native"}, {"code": "en", "level": "fluent"}],
        "projects": [],
        "certifications": [],
    },
}

JOB = {
    "title": "Python Developer",
    "description": "Je bouwt API's en datapijplijnen in Python voor onze klanten in een klein team.",
    "responsibilities": ["API's bouwen", "Datapijplijnen onderhouden"],
    "qualifications": ["Bachelor informatica"],
    "skills": [{"name": "Python", "is_required": True}, {"name": "SQL", "is_required": True}, {"name": "Kubernetes", "is_required": False}],
    "min_years_experience": 2,
    "education_level": "bachelor",
    "required_languages": ["nl"],
    "city": "Gent",
    "remote_policy": "hybrid",
    "employment_type": "full_time",
    "salary_min": 3500,
    "salary_max": 4500,
    "salary_period": "month",
    "industry": "IT & software",
    "status": "published",
}


def company_id(api: Api) -> str:
    return api.get("/auth/me").json()["companies"][0]["id"]


def create_job(api: Api, **overrides: Any) -> dict:
    response = api.post(f"/companies/{company_id(api)}/jobs", {**JOB, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def fill_profile(api: Api) -> None:
    response = api.patch("/candidates/me", PROFILE)
    assert response.status_code == 200, response.text
