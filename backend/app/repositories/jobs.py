"""Vacancy search queries (PostgreSQL full-text search + structured filters)."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Select, and_, desc, exists, func, literal, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Company, Job, JobSkill
from app.models.enums import JobStatus
from app.schemas.jobs import JobSearchParams
from app.utils import geo
from app.utils.skills import normalize_skill


def visible_jobs_query() -> Select[Any]:
    """Published vacancies whose deadline hasn't passed."""
    return (
        select(Job)
        .join(Company, Company.id == Job.company_id)
        .where(Job.status == JobStatus.PUBLISHED, or_(Job.application_deadline.is_(None), Job.application_deadline >= date.today()))
    )


def apply_filters(stmt: Select[Any], params: JobSearchParams) -> Select[Any]:
    if params.q:
        query = func.websearch_to_tsquery("simple", params.q)
        like = f"%{params.q.strip()}%"
        stmt = stmt.where(or_(Job.search_vector.op("@@")(query), Job.title.ilike(like), Company.name.ilike(like)))
    if params.company_id:
        stmt = stmt.where(Job.company_id == params.company_id)
    if params.city and not params.max_distance_km:
        stmt = stmt.where(Job.city.ilike(params.city.strip()))
    if params.remote:
        stmt = stmt.where(Job.remote_policy.in_(params.remote))
    if params.employment_type:
        stmt = stmt.where(Job.employment_type.in_(params.employment_type))
    if params.experience_level:
        stmt = stmt.where(Job.experience_level.in_(params.experience_level))
    if params.industry:
        stmt = stmt.where(func.lower(Job.industry).in_([i.lower() for i in params.industry]))
    if params.language:
        stmt = stmt.where(Job.language.in_(params.language))
    if params.salary_min_annual is not None:
        # Jobs without a stated salary are excluded when a salary filter is set: unknown is not "enough".
        stmt = stmt.where(func.coalesce(Job.salary_annual_max_eur, Job.salary_annual_min_eur) >= params.salary_min_annual)
    for skill in params.skills:
        normalized = normalize_skill(skill)
        stmt = stmt.where(exists().where(and_(JobSkill.job_id == Job.id, JobSkill.normalized_name == normalized)))
    return stmt


def search_ids(db: Session, params: JobSearchParams, *, limit: int = 2000) -> list[tuple[uuid.UUID, float]]:
    """All matching job ids with their text rank (used for relevance sorting), most relevant first."""
    stmt = apply_filters(visible_jobs_query(), params)
    rank = func.ts_rank(Job.search_vector, func.websearch_to_tsquery("simple", params.q)) if params.q else literal(0.0)
    orders: dict[str, list[Any]] = {
        "date": [desc(Job.published_at)],
        "salary": [desc(func.coalesce(Job.salary_annual_max_eur, Job.salary_annual_min_eur)).nulls_last(), desc(Job.published_at)],
    }
    order = orders.get(params.sort, [desc(rank), desc(Job.published_at)])
    rows = db.execute(stmt.with_only_columns(Job.id, rank, Job.city).order_by(*order).limit(limit)).all()
    if params.city and params.max_distance_km:
        rows = [
            r
            for r in rows
            if r[2] and (geo.same_place(r[2], params.city) or (geo.distance_km(r[2], params.city) or 1e9) <= params.max_distance_km)
        ]
    return [(r[0], float(r[1] or 0)) for r in rows]


def load_jobs(db: Session, ids: list[uuid.UUID]) -> list[Job]:
    if not ids:
        return []
    jobs = db.scalars(select(Job).where(Job.id.in_(ids)).options(selectinload(Job.skills), selectinload(Job.company))).all()
    by_id = {j.id: j for j in jobs}
    return [by_id[i] for i in ids if i in by_id]
