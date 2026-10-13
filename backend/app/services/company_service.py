import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.integrations.storage.local import get_storage
from app.models.entities import Company, CompanyMembership, Job, User
from app.models.enums import CompanyRole, JobStatus, UserRole
from app.schemas.jobs import CompanyBrief, CompanyIn, CompanyOut, CompanyUpdate, MemberOut
from app.services.audit import audit
from app.services.auth_service import normalize_email, unique_company_slug
from app.utils.files import detect_image_type


def logo_url(company: Company) -> str | None:
    if not company.logo_storage_key:
        return None
    # The key in the URL only busts caches; the file is looked up through the company id.
    return f"/api/v1/companies/{company.id}/logo?v={company.logo_storage_key[:8]}"


def brief(company: Company) -> CompanyBrief:
    return CompanyBrief(
        id=company.id,
        name=company.name,
        slug=company.slug,
        city=company.city,
        industry=company.industry,
        logo_url=logo_url(company),
        is_demo=company.is_demo,
    )


def membership(db: Session, user: User, company_id: uuid.UUID) -> CompanyMembership | None:
    return db.scalar(select(CompanyMembership).where(CompanyMembership.company_id == company_id, CompanyMembership.user_id == user.id))


def require_member(db: Session, user: User, company_id: uuid.UUID, *, owner: bool = False) -> Company:
    """Backend-enforced company access. Admins may manage every company."""
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Bedrijf niet gevonden.")
    if user.role == UserRole.ADMIN:
        return company
    member = membership(db, user, company_id)
    if member is None or (owner and member.role != CompanyRole.OWNER):
        raise PermissionDeniedError("Je hebt geen toegang tot dit bedrijf.")
    return company


def member_company_ids(db: Session, user: User) -> list[uuid.UUID]:
    return list(db.scalars(select(CompanyMembership.company_id).where(CompanyMembership.user_id == user.id)))


def company_out(db: Session, company: Company, viewer: User | None = None) -> CompanyOut:
    open_jobs = db.scalar(select(func.count()).select_from(Job).where(Job.company_id == company.id, Job.status == JobStatus.PUBLISHED)) or 0
    role = None
    if viewer is not None:
        m = membership(db, viewer, company.id)
        role = m.role.value if m else ("admin" if viewer.role == UserRole.ADMIN else None)
    return CompanyOut(
        **brief(company).model_dump(),
        description=company.description,
        website_url=company.website_url,
        size=company.size,
        open_jobs=open_jobs,
        created_at=company.created_at,
        viewer_role=role,
    )


def create_company(db: Session, user: User, body: CompanyIn) -> Company:
    if user.role not in (UserRole.EMPLOYER, UserRole.ADMIN):
        raise PermissionDeniedError("Alleen werkgeversaccounts kunnen een bedrijf aanmaken.")
    company = Company(**body.model_dump(), slug=unique_company_slug(db, body.name))
    db.add(company)
    db.flush()
    db.add(CompanyMembership(company_id=company.id, user_id=user.id, role=CompanyRole.OWNER))
    audit(db, "company.create", actor_id=user.id, target_type="company", target_id=company.id)
    db.commit()
    return company


def update_company(db: Session, user: User, company_id: uuid.UUID, body: CompanyUpdate) -> Company:
    company = require_member(db, user, company_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    db.commit()
    return company


def set_logo(db: Session, user: User, company_id: uuid.UUID, data: bytes) -> Company:
    company = require_member(db, user, company_id)
    if len(data) > get_settings().max_logo_bytes:
        raise AppError(f"Het logo mag maximaal {get_settings().max_logo_mb:g} MB groot zijn.", code="file_too_large", status_code=413)
    mime = detect_image_type(data)
    if mime is None:
        raise AppError("Upload een PNG-, JPEG- of WebP-afbeelding.", code="unsupported_file", status_code=415)
    storage = get_storage()
    old = company.logo_storage_key
    company.logo_storage_key = storage.save(data)
    company.logo_mime_type = mime
    db.commit()
    storage.delete(old)
    return company


def list_members(db: Session, user: User, company_id: uuid.UUID) -> list[MemberOut]:
    require_member(db, user, company_id)
    rows = db.execute(
        select(CompanyMembership, User)
        .join(User, User.id == CompanyMembership.user_id)
        .where(CompanyMembership.company_id == company_id)
        .order_by(User.full_name)
    )
    return [MemberOut(user_id=u.id, full_name=u.full_name, email=u.email, role=m.role.value) for m, u in rows]


def add_member(db: Session, user: User, company_id: uuid.UUID, email: str, role: str) -> None:
    require_member(db, user, company_id, owner=True)
    target = db.scalar(select(User).where(User.email == normalize_email(email)))
    # Same message whether the account doesn't exist or isn't an employer: no account enumeration.
    if target is None or target.role != UserRole.EMPLOYER:
        raise AppError(
            "Nodig een collega uit die al een werkgeversaccount heeft met dit e-mailadres.", code="member_not_found", status_code=404
        )
    if membership(db, target, company_id):
        raise ConflictError("Deze persoon is al lid van het bedrijf.")
    db.add(CompanyMembership(company_id=company_id, user_id=target.id, role=CompanyRole(role)))
    audit(db, "company.member_added", actor_id=user.id, target_type="company", target_id=company_id)
    db.commit()


def remove_member(db: Session, user: User, company_id: uuid.UUID, member_user_id: uuid.UUID) -> None:
    require_member(db, user, company_id, owner=True)
    member = db.scalar(
        select(CompanyMembership).where(CompanyMembership.company_id == company_id, CompanyMembership.user_id == member_user_id)
    )
    if member is None:
        raise NotFoundError("Lid niet gevonden.")
    owners = (
        db.scalar(
            select(func.count())
            .select_from(CompanyMembership)
            .where(CompanyMembership.company_id == company_id, CompanyMembership.role == CompanyRole.OWNER)
        )
        or 0
    )
    if member.role == CompanyRole.OWNER and owners <= 1:
        raise ConflictError("Een bedrijf heeft minstens één eigenaar nodig.")
    db.delete(member)
    audit(db, "company.member_removed", actor_id=user.id, target_type="company", target_id=company_id)
    db.commit()
