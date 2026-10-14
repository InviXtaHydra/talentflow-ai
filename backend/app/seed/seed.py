"""Development seed: demo companies, vacancies and accounts, all flagged `is_demo`."""

import logging
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.integrations.storage.local import get_storage
from app.models.entities import (
    CandidatePreference,
    CandidateProfile,
    Company,
    CompanyMembership,
    CVDocument,
    CVVersion,
    Job,
    User,
)
from app.models.enums import (
    CompanyRole,
    CVVersionKind,
    EducationLevel,
    EmploymentType,
    ExperienceLevel,
    ExtractionStatus,
    JobSource,
    JobStatus,
    RemotePolicy,
    SalaryPeriod,
    UserRole,
)
from app.schemas.jobs import JobSkillIn
from app.schemas.profile import ContactDetails, ExtractedCV, ProfileContent
from app.seed.demo_data import DEMO_CANDIDATE, DEMO_COMPANIES, DEMO_JOBS, demo_job_details
from app.services import tasks
from app.services.auth_service import create_user, unique_company_slug
from app.services.cv.content import profile_to_cv_content
from app.services.documents.pdf import render_pdf
from app.services.job_service import _refresh_derived, _set_skills
from app.utils.files import PDF_MIME
from app.utils.text import content_hash

logger = logging.getLogger("talentflow.seed")

DEMO_CANDIDATE_EMAIL = "demo.kandidaat@example.com"
DEMO_EMPLOYER_EMAIL = "demo.werkgever@example.com"


def seed_jobs(db: Session) -> int:
    companies: dict[str, Company] = {}
    for data in DEMO_COMPANIES:
        company = db.scalar(select(Company).where(Company.name == data["name"], Company.is_demo.is_(True)))
        if company is None:
            company = Company(
                name=data["name"],
                slug=unique_company_slug(db, data["name"]),
                industry=data["industry"],
                city=data["city"],
                size=data["size"],
                description=data["description"],
                is_demo=True,
            )
            db.add(company)
            db.flush()
        companies[data["key"]] = company
    created = 0
    now = utcnow()
    for index, data in enumerate(DEMO_JOBS):
        external_id = f"demo-{index:03d}"
        existing = db.scalar(select(Job).where(Job.source == JobSource.DEMO, Job.external_id == external_id))
        if existing is not None:
            # Demo vacancies seeded before the detail fields existed get them filled in once.
            if not existing.benefits and not existing.hiring_process:
                for key, value in demo_job_details(index, data).items():
                    setattr(existing, key, value)
            continue
        salary = data["salary"]
        job = Job(
            company_id=companies[data["company"]].id,
            title=data["title"],
            description=data["description"],
            responsibilities=data["responsibilities"],
            qualifications=data["qualifications"],
            min_years_experience=data["years"],
            experience_level=ExperienceLevel(data["level"]),
            education_level=EducationLevel(data["education"]) if data["education"] else None,
            required_languages=data["languages"],
            city=data["city"],
            remote_policy=RemotePolicy(data["remote"]),
            employment_type=EmploymentType(data["type"]),
            salary_min=salary[0] if salary else None,
            salary_max=salary[1] if salary else None,
            salary_period=SalaryPeriod(salary[2]) if salary else None,
            salary_currency="EUR",
            industry=data["industry"],
            language=data["lang"],
            status=JobStatus.PUBLISHED,
            published_at=now - timedelta(days=index % 21, hours=index),
            source=JobSource.DEMO,
            external_id=external_id,
            is_demo=True,
            application_url=None,
            **demo_job_details(index, data),
        )
        _set_skills(job, [JobSkillIn(name=n, is_required=r) for n, r in data["skills"]])
        db.add(job)
        db.flush()
        _refresh_derived(db, job)
        tasks.enqueue(
            db,
            "embed_job",
            user_id=None,
            payload={"job_id": str(job.id)},
            idempotency_key=f"embed_job:{job.id}",
            max_attempts=3,
            timeout_seconds=120,
            commit=False,
        )
        created += 1
    db.commit()
    return created


def seed_accounts(db: Session, password: str) -> list[str]:
    created = []
    if db.scalar(select(User.id).where(User.email == DEMO_CANDIDATE_EMAIL)) is None:
        data = DEMO_CANDIDATE
        user = create_user(
            db,
            email=DEMO_CANDIDATE_EMAIL,
            password=password,
            full_name=data["full_name"],
            role=UserRole.CANDIDATE,
            is_demo=True,
            verified=True,
        )
        db.flush()
        profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        prefs = db.scalar(select(CandidatePreference).where(CandidatePreference.user_id == user.id))
        assert profile is not None and prefs is not None
        profile.headline, profile.summary, profile.city, profile.phone = data["headline"], data["summary"], data["city"], data["phone"]
        profile.content = ProfileContent.model_validate(data["content"]).model_dump(mode="json")
        profile.content_hash = content_hash([profile.headline, profile.summary, profile.city, profile.content])
        profile.confirmed_at = profile.onboarding_completed_at = utcnow()
        for key, value in data["preferences"].items():
            setattr(prefs, key, value)
        db.flush()

        # A demo source CV: rendered from the demo profile, so the CV library and the optimizer have a real document.
        cv_content = profile_to_cv_content(user, profile)
        pdf = render_pdf(cv_content, template="minimal", language="nl", title="CV Lotte Peeters")
        extracted = ExtractedCV(
            language="nl",
            contact=ContactDetails(full_name=user.full_name, email=user.email, phone=profile.phone, city=profile.city),
            headline=profile.headline,
            summary=profile.summary,
            profile=ProfileContent.model_validate(profile.content),
        )
        document = CVDocument(
            user_id=user.id,
            original_filename="cv-lotte-peeters-demo.pdf",
            storage_key=get_storage().save(pdf),
            mime_type=PDF_MIME,
            size_bytes=len(pdf),
            sha256=content_hash(pdf.hex()),
            language="nl",
            extraction_status=ExtractionStatus.COMPLETED,
            extraction_method="demo",
            extracted_data=extracted.model_dump(mode="json"),
            confirmed_at=utcnow(),
            is_demo=True,
        )
        db.add(document)
        db.flush()
        content = cv_content.model_dump(mode="json")
        db.add(
            CVVersion(
                user_id=user.id,
                source_cv_id=document.id,
                kind=CVVersionKind.ORIGINAL,
                title="Origineel: cv-lotte-peeters-demo.pdf",
                language="nl",
                template="minimal",
                content=content,
                generated_content=content,
            )
        )
        tasks.enqueue(
            db,
            "embed_profile",
            user_id=user.id,
            payload={"user_id": str(user.id)},
            idempotency_key=f"embed_profile:{user.id}",
            max_attempts=3,
            timeout_seconds=120,
            commit=False,
        )
        created.append(DEMO_CANDIDATE_EMAIL)

    if db.scalar(select(User.id).where(User.email == DEMO_EMPLOYER_EMAIL)) is None:
        employer = create_user(
            db, email=DEMO_EMPLOYER_EMAIL, password=password, full_name="Jonas Claes", role=UserRole.EMPLOYER, is_demo=True, verified=True
        )
        db.flush()
        company = db.scalar(select(Company).where(Company.name == "Brightcode Studio", Company.is_demo.is_(True)))
        if company:
            db.add(CompanyMembership(company_id=company.id, user_id=employer.id, role=CompanyRole.OWNER))
        created.append(DEMO_EMPLOYER_EMAIL)
    db.commit()
    return created


def run(db: Session, password: str | None) -> dict:
    jobs = seed_jobs(db)
    generated = password is None
    password = password or secrets.token_urlsafe(12)
    accounts = seed_accounts(db, password)
    return {"jobs_created": jobs, "accounts_created": accounts, "password": password if accounts else None, "password_generated": generated}
