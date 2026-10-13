import uuid

from fastapi import APIRouter, File, Response, UploadFile
from sqlalchemy import func, or_, select

from app.api.deps import DbSession, EmployerUser, OptionalUser
from app.core.errors import NotFoundError
from app.integrations.storage.local import get_storage
from app.models.entities import Company, Job
from app.models.enums import JobStatus
from app.schemas.common import Message, Page, page_count
from app.schemas.jobs import AddMemberRequest, CompanyIn, CompanyOut, CompanyUpdate, JobSummaryOut, MemberOut
from app.services import company_service, job_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=Page[CompanyOut])
def list_companies(
    db: DbSession, user: OptionalUser, q: str | None = None, industry: str | None = None, page: int = 1, page_size: int = 24
) -> Page[CompanyOut]:
    page_size = max(1, min(page_size, 50))
    open_jobs = (
        select(func.count()).select_from(Job).where(Job.company_id == Company.id, Job.status == JobStatus.PUBLISHED).scalar_subquery()
    )
    stmt = select(Company)
    if q:
        stmt = stmt.where(or_(Company.name.ilike(f"%{q}%"), Company.industry.ilike(f"%{q}%")))
    if industry:
        stmt = stmt.where(Company.industry.ilike(industry))
    # The public directory lists companies with at least one open vacancy.
    stmt = stmt.where(open_jobs > 0)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(open_jobs.desc(), Company.name).offset((max(page, 1) - 1) * page_size).limit(page_size))
    items = [company_service.company_out(db, c, user) for c in rows]
    return Page(items=items, total=total, page=page, page_size=page_size, pages=page_count(total, page_size))


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(body: CompanyIn, db: DbSession, user: EmployerUser) -> CompanyOut:
    return company_service.company_out(db, company_service.create_company(db, user, body), user)


def _company(db, company_id: uuid.UUID) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Bedrijf niet gevonden.")
    return company


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: uuid.UUID, db: DbSession, user: OptionalUser) -> CompanyOut:
    return company_service.company_out(db, _company(db, company_id), user)


@router.get("/{company_id}/jobs", response_model=list[JobSummaryOut])
def company_jobs(company_id: uuid.UUID, db: DbSession, user: OptionalUser) -> list[JobSummaryOut]:
    return job_service.company_jobs(db, user, _company(db, company_id))


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(company_id: uuid.UUID, body: CompanyUpdate, db: DbSession, user: EmployerUser) -> CompanyOut:
    return company_service.company_out(db, company_service.update_company(db, user, company_id, body), user)


@router.post("/{company_id}/logo", response_model=CompanyOut)
async def upload_logo(company_id: uuid.UUID, db: DbSession, user: EmployerUser, file: UploadFile = File(...)) -> CompanyOut:
    data = await file.read(5 * 1024 * 1024)
    return company_service.company_out(db, company_service.set_logo(db, user, company_id, data), user)


@router.get("/{company_id}/logo", summary="Public company logo")
def get_logo(company_id: uuid.UUID, db: DbSession) -> Response:
    company = _company(db, company_id)
    if not company.logo_storage_key or not company.logo_mime_type:
        raise NotFoundError("Geen logo.")
    return Response(
        get_storage().read(company.logo_storage_key),
        media_type=company.logo_mime_type,
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{company_id}/members", response_model=list[MemberOut])
def members(company_id: uuid.UUID, db: DbSession, user: EmployerUser) -> list[MemberOut]:
    return company_service.list_members(db, user, company_id)


@router.post("/{company_id}/members", response_model=Message, status_code=201)
def add_member(company_id: uuid.UUID, body: AddMemberRequest, db: DbSession, user: EmployerUser) -> Message:
    company_service.add_member(db, user, company_id, body.email, body.role)
    return Message(message="Collega toegevoegd.")


@router.delete("/{company_id}/members/{member_user_id}", response_model=Message)
def remove_member(company_id: uuid.UUID, member_user_id: uuid.UUID, db: DbSession, user: EmployerUser) -> Message:
    company_service.remove_member(db, user, company_id, member_user_id)
    return Message(message="Collega verwijderd.")
