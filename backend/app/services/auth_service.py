import re
import uuid
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ConflictError, NotFoundError
from app.core.security import hash_password, hash_token, new_token, password_needs_rehash, verify_password
from app.db.base import utcnow
from app.integrations.email.sender import send_email
from app.integrations.email.templates import password_reset_email, verification_email
from app.models.entities import (
    AuthToken,
    CandidatePreference,
    CandidateProfile,
    Company,
    CompanyMembership,
    User,
    UserSession,
)
from app.models.enums import CompanyRole, TokenPurpose, UserRole
from app.services.audit import audit

VERIFY_TTL = timedelta(hours=48)
RESET_TTL = timedelta(hours=1)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def slugify(value: str) -> str:
    import unicodedata

    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:200] or "bedrijf"


def unique_company_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug, n = base, 2
    while db.scalar(select(Company.id).where(Company.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def create_user(
    db: Session, *, email: str, password: str, full_name: str, role: UserRole, is_demo: bool = False, verified: bool = False
) -> User:
    email = normalize_email(email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise ConflictError("Er bestaat al een account met dit e-mailadres.", code="email_taken")
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_demo=is_demo,
        email_verified_at=utcnow() if verified else None,
    )
    db.add(user)
    db.flush()
    if role == UserRole.CANDIDATE:
        db.add(CandidateProfile(user_id=user.id, content={}, is_demo=is_demo))
        db.add(CandidatePreference(user_id=user.id))
    return user


def register(
    db: Session, *, email: str, password: str, full_name: str, account_type: str, company_name: str | None, ip: str | None
) -> User:
    role = UserRole.EMPLOYER if account_type == "employer" else UserRole.CANDIDATE
    user = create_user(db, email=email, password=password, full_name=full_name, role=role)
    if role == UserRole.EMPLOYER and company_name:
        company = Company(name=company_name, slug=unique_company_slug(db, company_name))
        db.add(company)
        db.flush()
        db.add(CompanyMembership(company_id=company.id, user_id=user.id, role=CompanyRole.OWNER))
    audit(db, "auth.register", actor_id=user.id, target_type="user", target_id=user.id, ip=ip, details={"role": role.value})
    db.commit()
    send_verification(db, user)
    return user


def _issue_token(db: Session, user: User, purpose: TokenPurpose, ttl: timedelta) -> str:
    db.execute(delete(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == purpose, AuthToken.used_at.is_(None)))
    token = new_token()
    db.add(AuthToken(user_id=user.id, purpose=purpose, token_hash=hash_token(token), expires_at=utcnow() + ttl))
    db.commit()
    return token


def _consume_token(db: Session, token: str, purpose: TokenPurpose) -> User:
    record = db.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(token), AuthToken.purpose == purpose))
    if record is None or record.used_at is not None or record.expires_at <= utcnow():
        raise AuthenticationError("Deze link is ongeldig of verlopen. Vraag een nieuwe aan.", code="invalid_token")
    record.used_at = utcnow()
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Deze link is ongeldig of verlopen. Vraag een nieuwe aan.", code="invalid_token")
    return user


def send_verification(db: Session, user: User) -> None:
    if user.email_verified_at is not None:
        return
    token = _issue_token(db, user, TokenPurpose.VERIFY_EMAIL, VERIFY_TTL)
    send_email(verification_email(user.email, user.full_name, token))


def verify_email(db: Session, token: str) -> User:
    user = _consume_token(db, token, TokenPurpose.VERIFY_EMAIL)
    user.email_verified_at = user.email_verified_at or utcnow()
    audit(db, "auth.email_verified", actor_id=user.id, target_type="user", target_id=user.id)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    # verify_password also runs for unknown accounts, so timing doesn't reveal which e-mail addresses exist.
    valid = verify_password(password, user.password_hash if user else None)
    if not user or not valid or not user.is_active:
        raise AuthenticationError("E-mailadres of wachtwoord is onjuist.", code="invalid_credentials")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


def create_session(db: Session, user: User, user_agent: str | None, ip: str | None) -> tuple[str, str]:
    token, csrf = new_token(), new_token()
    now = utcnow()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            csrf_token=csrf,
            expires_at=now + timedelta(hours=get_settings().session_ttl_hours),
            user_agent=(user_agent or "")[:300] or None,
        )
    )
    user.last_login_at = now
    user.last_active_at = now
    audit(db, "auth.login", actor_id=user.id, target_type="user", target_id=user.id, ip=ip)
    db.commit()
    return token, csrf


def end_session(db: Session, session: UserSession) -> None:
    db.delete(session)
    db.commit()


def request_password_reset(db: Session, email: str, ip: str | None) -> None:
    """Always behaves the same from the outside, whether or not the account exists (no enumeration)."""
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not user.is_active:
        return
    token = _issue_token(db, user, TokenPurpose.RESET_PASSWORD, RESET_TTL)
    audit(db, "auth.password_reset_requested", actor_id=user.id, target_type="user", target_id=user.id, ip=ip)
    db.commit()
    send_email(password_reset_email(user.email, user.full_name, token))


def reset_password(db: Session, token: str, password: str, ip: str | None) -> None:
    user = _consume_token(db, token, TokenPurpose.RESET_PASSWORD)
    user.password_hash = hash_password(password)
    # A reset logs out every device. Clicking the e-mail link also proves the address.
    user.email_verified_at = user.email_verified_at or utcnow()
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    audit(db, "auth.password_reset", actor_id=user.id, target_type="user", target_id=user.id, ip=ip)
    db.commit()


def change_password(db: Session, user: User, current: str, new: str, keep_session_id: uuid.UUID) -> None:
    if not verify_password(current, user.password_hash):
        raise AuthenticationError("Je huidige wachtwoord is onjuist.", code="invalid_credentials")
    user.password_hash = hash_password(new)
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.id != keep_session_id))
    audit(db, "auth.password_changed", actor_id=user.id, target_type="user", target_id=user.id)
    db.commit()


def revoke_session(db: Session, user: User, session_id: uuid.UUID) -> None:
    session = db.get(UserSession, session_id)
    if session is None or session.user_id != user.id:
        raise NotFoundError("Sessie niet gevonden.")
    db.delete(session)
    db.commit()
