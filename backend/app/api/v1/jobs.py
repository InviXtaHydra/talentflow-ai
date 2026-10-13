import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CandidateUser, DbSession, EmployerUser, OptionalUser
from app.core.config import get_matching_weights
from app.core.errors import AppError
from app.models.enums import EmploymentType, ExperienceLevel, JobStatus, RemotePolicy
from app.schemas.common import Message, Page
from app.schemas.jobs import FacetsOut, JobDetailOut, JobIn, JobSearchParams, JobSummaryOut, JobUpdate, MatchOut
from app.services import job_service
from app.services.matching import service as matching

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=Page[JobSummaryOut])
def search_jobs(
    db: DbSession,
    user: OptionalUser,
    q: str | None = None,
    company_id: uuid.UUID | None = None,
    city: str | None = None,
    max_distance_km: int | None = None,
    remote: Annotated[list[RemotePolicy], Query()] = [],  # noqa: B006
    employment_type: Annotated[list[EmploymentType], Query()] = [],  # noqa: B006
    experience_level: Annotated[list[ExperienceLevel], Query()] = [],  # noqa: B006
    industry: Annotated[list[str], Query()] = [],  # noqa: B006
    skills: Annotated[list[str], Query()] = [],  # noqa: B006
    language: Annotated[list[str], Query()] = [],  # noqa: B006
    salary_min_annual: int | None = None,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 20,
) -> Page[JobSummaryOut]:
    params = JobSearchParams(
        q=q,
        company_id=company_id,
        city=city,
        max_distance_km=max_distance_km,
        remote=remote,
        employment_type=employment_type,
        experience_level=experience_level,
        industry=industry,
        skills=skills,
        language=language,
        salary_min_annual=salary_min_annual,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return job_service.search(db, user, params)


@router.get("/jobs/facets", response_model=FacetsOut)
def facets(db: DbSession) -> FacetsOut:
    return job_service.facets(db)


@router.get("/jobs/recommendations", response_model=list[JobSummaryOut])
def recommendations(db: DbSession, user: CandidateUser, limit: int = Query(default=10, ge=1, le=50)) -> list[JobSummaryOut]:
    return [job_service.summary(job, match=m) for job, m in matching.recommendations(db, user, limit=limit)]


@router.get("/jobs/saved", response_model=list[JobSummaryOut])
def saved(db: DbSession, user: CandidateUser) -> list[JobSummaryOut]:
    return job_service.saved_jobs(db, user)


@router.get("/jobs/compare", response_model=list[JobDetailOut])
def compare(db: DbSession, user: OptionalUser, ids: Annotated[list[uuid.UUID], Query(max_length=4)]) -> list[JobDetailOut]:
    if not 2 <= len(ids) <= 4:
        raise AppError("Kies twee tot vier vacatures om te vergelijken.", code="validation_error", status_code=422)
    return [job_service.detail(db, user, job_service.get_visible_job(db, user, i)) for i in dict.fromkeys(ids)]


@router.get("/jobs/{job_id}", response_model=JobDetailOut)
def get_job(job_id: uuid.UUID, db: DbSession, user: OptionalUser) -> JobDetailOut:
    return job_service.detail(db, user, job_service.get_visible_job(db, user, job_id))


@router.get("/jobs/{job_id}/related", response_model=list[JobSummaryOut])
def related(job_id: uuid.UUID, db: DbSession, user: OptionalUser) -> list[JobSummaryOut]:
    return job_service.related(db, user, job_service.get_visible_job(db, user, job_id))


@router.get("/jobs/{job_id}/match", response_model=MatchOut)
def job_match(job_id: uuid.UUID, db: DbSession, user: CandidateUser) -> MatchOut:
    job = job_service.get_visible_job(db, user, job_id)
    if job.status != JobStatus.PUBLISHED:
        raise AppError("Voor gesloten vacatures wordt geen match meer berekend.", code="job_not_open", status_code=409)
    match = matching.get_or_compute(db, user, [job])[job.id]
    return MatchOut(
        job_id=job.id,
        score=match.score,
        status=match.result.get("status", "ok"),
        result=match.result,
        algorithm_version=match.algorithm_version,
        calculated_at=match.calculated_at,
        weights=get_matching_weights().model_dump(),
    )


@router.post("/jobs/{job_id}/save", response_model=Message)
def save(job_id: uuid.UUID, db: DbSession, user: CandidateUser) -> Message:
    job_service.save_job(db, user, job_id)
    return Message(message="Vacature bewaard.")


@router.delete("/jobs/{job_id}/save", response_model=Message)
def unsave(job_id: uuid.UUID, db: DbSession, user: CandidateUser) -> Message:
    job_service.unsave_job(db, user, job_id)
    return Message(message="Vacature niet meer bewaard.")


@router.post("/companies/{company_id}/jobs", response_model=JobDetailOut, status_code=201)
def create_job(company_id: uuid.UUID, body: JobIn, db: DbSession, user: EmployerUser) -> JobDetailOut:
    job = job_service.create_job(db, user, company_id, body)
    return job_service.detail(db, user, job_service.get_job(db, job.id))


@router.patch("/jobs/{job_id}", response_model=JobDetailOut)
def update_job(job_id: uuid.UUID, body: JobUpdate, db: DbSession, user: EmployerUser) -> JobDetailOut:
    job = job_service.update_job(db, user, job_id, body)
    return job_service.detail(db, user, job_service.get_job(db, job.id))
