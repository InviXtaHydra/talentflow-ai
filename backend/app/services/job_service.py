import uuid
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, NotFoundError, PermissionDeniedError
from app.db.base import utcnow
from app.models.entities import Application, Company, Job, JobSkill, JobView, SavedJob, User
from app.models.enums import JobSource, JobStatus, UserRole
from app.repositories import jobs as job_repo
from app.schemas.common import Page, page_count
from app.schemas.jobs import (
    ApplicationBrief,
    FacetsOut,
    JobDetailOut,
    JobIn,
    JobSearchParams,
    JobSkillIn,
    JobSkillOut,
    JobSummaryOut,
    JobUpdate,
)
from app.services import tasks
from app.services.company_service import brief as company_brief
from app.services.company_service import membership, require_member
from app.services.matching import service as matching
from app.utils.salary import to_annual_eur
from app.utils.skills import normalize_skill
from app.utils.text import content_hash


def _set_skills(job: Job, skills: list[JobSkillIn]) -> None:
    seen: dict[str, JobSkill] = {}
    for position, skill in enumerate(skills):
        normalized = normalize_skill(skill.name)
        if not normalized or normalized in seen:
            continue
        seen[normalized] = JobSkill(name=skill.name.strip(), normalized_name=normalized, is_required=skill.is_required, position=position)
    job.skills = list(seen.values())


def _refresh_derived(db: Session, job: Job) -> None:
    job.salary_annual_min_eur = to_annual_eur(job.salary_min, job.salary_period, job.salary_currency)
    job.salary_annual_max_eur = to_annual_eur(job.salary_max, job.salary_period, job.salary_currency)
    job.content_hash = content_hash(
        [
            job.title,
            job.description,
            job.responsibilities,
            job.qualifications,
            [(s.normalized_name, s.is_required) for s in job.skills],
            job.min_years_experience,
            job.experience_level,
            job.education_level,
            job.required_languages,
            job.city,
            job.remote_policy,
            job.employment_type,
            job.salary_annual_min_eur,
            job.salary_annual_max_eur,
            job.industry,
        ]
    )


def _schedule_embedding(db: Session, job: Job) -> None:
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


def _require_verified_to_publish(user: User) -> None:
    if user.role != UserRole.ADMIN and user.email_verified_at is None:
        raise PermissionDeniedError("Bevestig eerst je e-mailadres voordat je vacatures publiceert.", code="email_not_verified")


def create_job(db: Session, user: User, company_id: uuid.UUID, body: JobIn) -> Job:
    company = require_member(db, user, company_id)
    if body.status == "published":
        _require_verified_to_publish(user)
    data = body.model_dump(exclude={"skills", "status"})
    job = Job(**data, company_id=company.id, created_by_user_id=user.id, source=JobSource.EMPLOYER, status=JobStatus(body.status))
    _set_skills(job, body.skills)
    if job.status == JobStatus.PUBLISHED:
        job.published_at = utcnow()
    db.add(job)
    db.flush()
    _refresh_derived(db, job)
    _schedule_embedding(db, job)
    db.commit()
    return job


def get_job(db: Session, job_id: uuid.UUID) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id).options(selectinload(Job.skills), selectinload(Job.company)))
    if job is None:
        raise NotFoundError("Vacature niet gevonden.")
    return job


def can_manage(db: Session, user: User | None, job: Job) -> bool:
    if user is None:
        return False
    return user.role == UserRole.ADMIN or membership(db, user, job.company_id) is not None


def get_visible_job(db: Session, user: User | None, job_id: uuid.UUID) -> Job:
    """Published and closed vacancies are public (closed ones stay readable for saved links and applications);
    drafts only for the company's own members."""
    job = get_job(db, job_id)
    if job.status == JobStatus.DRAFT and not can_manage(db, user, job):
        raise NotFoundError("Vacature niet gevonden.")
    return job


def update_job(db: Session, user: User, job_id: uuid.UUID, body: JobUpdate) -> Job:
    job = get_job(db, job_id)
    require_member(db, user, job.company_id)
    data = body.model_dump(exclude_unset=True, exclude={"skills", "status"})
    for key, value in data.items():
        setattr(job, key, value)
    if body.skills is not None:
        _set_skills(job, body.skills)
    if body.status is not None and body.status != job.status:
        if body.status == JobStatus.PUBLISHED:
            _require_verified_to_publish(user)
            job.published_at = job.published_at or utcnow()
            job.closed_at = None
        elif body.status == JobStatus.CLOSED:
            job.closed_at = utcnow()
        job.status = body.status
    if job.salary_min is not None and job.salary_max is not None and job.salary_min > job.salary_max:
        raise AppError("Het minimumloon mag niet hoger zijn dan het maximum.", code="validation_error", status_code=422)
    job.updated_at = utcnow()
    _refresh_derived(db, job)
    _schedule_embedding(db, job)
    db.commit()
    return job


def summary(job: Job, *, saved: bool = False, match=None) -> JobSummaryOut:
    return JobSummaryOut(
        id=job.id,
        title=job.title,
        company=company_brief(job.company),
        city=job.city,
        remote_policy=job.remote_policy,
        employment_type=job.employment_type,
        experience_level=job.experience_level,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        salary_period=job.salary_period,
        industry=job.industry,
        language=job.language,
        status=job.status,
        published_at=job.published_at,
        application_deadline=job.application_deadline,
        is_demo=job.is_demo,
        skills=[JobSkillOut(name=s.name, is_required=s.is_required) for s in job.skills],
        saved=saved,
        match=matching.brief(match),
    )


def detail(db: Session, user: User | None, job: Job) -> JobDetailOut:
    saved = False
    match = None
    application = None
    if user is not None and user.role == UserRole.CANDIDATE:
        saved = db.scalar(select(SavedJob.id).where(SavedJob.user_id == user.id, SavedJob.job_id == job.id)) is not None
        if job.status == JobStatus.PUBLISHED:
            match = matching.get_or_compute(db, user, [job])[job.id]
        app = db.scalar(select(Application).where(Application.user_id == user.id, Application.job_id == job.id))
        if app:
            application = ApplicationBrief(id=app.id, status=app.status.value, channel=app.channel.value)
        _record_view(db, user, job)
    base = summary(job, saved=saved, match=match)
    return JobDetailOut(
        **base.model_dump(),
        description=job.description,
        responsibilities=job.responsibilities or [],
        qualifications=job.qualifications or [],
        min_years_experience=job.min_years_experience,
        education_level=job.education_level,
        required_languages=job.required_languages or [],
        application_url=job.application_url,
        source=job.source.value,
        created_at=job.created_at,
        updated_at=job.updated_at,
        application=application,
        can_edit=can_manage(db, user, job),
    )


def _record_view(db: Session, user: User, job: Job) -> None:
    view = db.scalar(select(JobView).where(JobView.user_id == user.id, JobView.job_id == job.id))
    if view is None:
        db.add(JobView(user_id=user.id, job_id=job.id))
    else:
        view.viewed_at = utcnow()
    db.commit()


def _score_key(score: int | None) -> int:
    return -1 if score is None else score


def search(db: Session, user: User | None, params: JobSearchParams) -> Page[JobSummaryOut]:
    ids_with_rank = job_repo.search_ids(db, params)
    ids = [i for i, _ in ids_with_rank]
    is_candidate = user is not None and user.role == UserRole.CANDIDATE
    matches = {}
    if is_candidate and params.sort == "match":
        all_jobs = job_repo.load_jobs(db, ids)
        assert user is not None
        matches = matching.get_or_compute(db, user, all_jobs)
        ids.sort(key=lambda i: _score_key(matches[i].score), reverse=True)
    total = len(ids)
    start = (params.page - 1) * params.page_size
    page_ids = ids[start : start + params.page_size]
    jobs = job_repo.load_jobs(db, page_ids)
    saved: set[uuid.UUID] = set()
    if is_candidate:
        assert user is not None
        if not matches:
            matches = matching.get_or_compute(db, user, jobs)
        saved = set(db.scalars(select(SavedJob.job_id).where(SavedJob.user_id == user.id, SavedJob.job_id.in_(page_ids))))
    items = [summary(j, saved=j.id in saved, match=matches.get(j.id)) for j in jobs]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size, pages=page_count(total, params.page_size))


def related(db: Session, user: User | None, job: Job, limit: int = 4) -> list[JobSummaryOut]:
    skill_names = [s.normalized_name for s in job.skills]
    stmt = job_repo.visible_jobs_query().where(Job.id != job.id)
    overlap = (
        select(func.count())
        .select_from(JobSkill)
        .where(JobSkill.job_id == Job.id, JobSkill.normalized_name.in_(skill_names))
        .scalar_subquery()
    )
    same_industry = case((func.lower(Job.industry) == (job.industry or "").lower(), 1), else_=0)
    rows = (
        db.execute(stmt.with_only_columns(Job.id).order_by((overlap * 2 + same_industry).desc(), Job.published_at.desc()).limit(limit))
        .scalars()
        .all()
    )
    return [summary(j) for j in job_repo.load_jobs(db, list(rows))]


def facets(db: Session) -> FacetsOut:
    base = job_repo.visible_jobs_query().subquery()
    industries = db.scalars(select(base.c.industry).where(base.c.industry.is_not(None)).distinct().order_by(base.c.industry)).all()
    cities = db.scalars(select(base.c.city).where(base.c.city.is_not(None)).distinct().order_by(base.c.city)).all()
    skills = db.scalars(
        select(JobSkill.name).where(JobSkill.job_id.in_(select(base.c.id))).group_by(JobSkill.name).order_by(func.count().desc()).limit(40)
    ).all()
    return FacetsOut(industries=list(industries), cities=list(cities), skills=list(skills))


def save_job(db: Session, user: User, job_id: uuid.UUID) -> None:
    get_visible_job(db, user, job_id)
    if db.scalar(select(SavedJob.id).where(SavedJob.user_id == user.id, SavedJob.job_id == job_id)) is None:
        db.add(SavedJob(user_id=user.id, job_id=job_id))
        db.commit()


def unsave_job(db: Session, user: User, job_id: uuid.UUID) -> None:
    saved = db.scalar(select(SavedJob).where(SavedJob.user_id == user.id, SavedJob.job_id == job_id))
    if saved:
        db.delete(saved)
        db.commit()


def saved_jobs(db: Session, user: User) -> list[JobSummaryOut]:
    ids = list(db.scalars(select(SavedJob.job_id).where(SavedJob.user_id == user.id).order_by(SavedJob.created_at.desc())))
    jobs = job_repo.load_jobs(db, ids)
    published = [j for j in jobs if j.status == JobStatus.PUBLISHED]
    matches = matching.get_or_compute(db, user, published)
    return [summary(j, saved=True, match=matches.get(j.id)) for j in jobs]


def company_jobs(db: Session, viewer: User | None, company: Company) -> list[JobSummaryOut]:
    stmt = select(Job).where(Job.company_id == company.id).options(selectinload(Job.skills), selectinload(Job.company))
    if not (viewer and can_manage_company(db, viewer, company)):
        stmt = stmt.where(
            Job.status == JobStatus.PUBLISHED, (Job.application_deadline.is_(None)) | (Job.application_deadline >= date.today())
        )
    return [summary(j) for j in db.scalars(stmt.order_by(Job.created_at.desc()))]


def can_manage_company(db: Session, user: User, company: Company) -> bool:
    return user.role == UserRole.ADMIN or membership(db, user, company.id) is not None
