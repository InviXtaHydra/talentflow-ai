from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import CandidateProfile, Company, CompanyMembership, User
from app.schemas.auth import CompanyRef, UserOut


def user_out(db: Session, user: User) -> UserOut:
    companies = [
        CompanyRef(id=c.id, name=c.name, slug=c.slug, role=m.role.value)
        for m, c in db.execute(
            select(CompanyMembership, Company)
            .join(Company, Company.id == CompanyMembership.company_id)
            .where(CompanyMembership.user_id == user.id)
            .order_by(Company.name)
        ).all()
    ]
    onboarding = db.scalar(select(CandidateProfile.onboarding_completed_at).where(CandidateProfile.user_id == user.id))
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        locale=user.locale,
        email_verified=user.email_verified_at is not None,
        onboarding_completed=onboarding is not None,
        ai_processing_consent=user.ai_processing_consent_at is not None,
        is_demo=user.is_demo,
        companies=companies,
        created_at=user.created_at,
    )
