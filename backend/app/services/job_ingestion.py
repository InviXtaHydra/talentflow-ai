"""Ingestion of vacancies from authorized feeds/APIs.

Only for sources the platform has permission to use (partner feeds, public-sector APIs with open
licences, ...). There is deliberately no scraper. A feed adapter converts its source format into
`FeedJob` items; `ingest()` upserts them by (source, external_id)."""

import uuid
from typing import Protocol

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.entities import Company, Job
from app.models.enums import JobSource, JobStatus
from app.schemas.jobs import _JobFields
from app.services.job_service import _refresh_derived, _schedule_embedding, _set_skills


class FeedJob(_JobFields):
    external_id: str = Field(min_length=1, max_length=200)


class FeedBatch(BaseModel):
    company_id: uuid.UUID
    jobs: list[FeedJob] = Field(max_length=500)
    close_missing: bool = False


class JobFeedAdapter(Protocol):
    """Implement this for a specific, authorized feed (e.g. a partner ATS export)."""

    source_name: str

    def fetch(self) -> list[FeedJob]: ...


def ingest(db: Session, company: Company, items: list[FeedJob], *, close_missing: bool = False) -> dict[str, int]:
    created = updated = closed = 0
    seen: set[str] = set()
    for item in items:
        seen.add(item.external_id)
        job = db.scalar(select(Job).where(Job.source == JobSource.FEED, Job.external_id == item.external_id))
        data = item.model_dump(exclude={"skills", "external_id"})
        if job is None:
            job = Job(
                **data,
                company_id=company.id,
                source=JobSource.FEED,
                external_id=item.external_id,
                status=JobStatus.PUBLISHED,
                published_at=utcnow(),
            )
            db.add(job)
            created += 1
        else:
            for key, value in data.items():
                setattr(job, key, value)
            job.updated_at = utcnow()
            updated += 1
        _set_skills(job, item.skills)
        db.flush()
        _refresh_derived(db, job)
        _schedule_embedding(db, job)
    if close_missing:
        for job in db.scalars(
            select(Job).where(Job.company_id == company.id, Job.source == JobSource.FEED, Job.status == JobStatus.PUBLISHED)
        ):
            if job.external_id not in seen:
                job.status = JobStatus.CLOSED
                job.closed_at = utcnow()
                closed += 1
    db.commit()
    return {"created": created, "updated": updated, "closed": closed}
