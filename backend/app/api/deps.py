import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import hash_token
from app.db.base import utcnow
from app.db.session import get_db
from app.models.entities import User, UserSession
from app.models.enums import UserRole

SESSION_COOKIE = "tf_session"
CSRF_COOKIE = "tf_csrf"
CSRF_HEADER = "x-csrf-token"

DbSession = Annotated[Session, Depends(get_db)]


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _load_session(request: Request, db: Session) -> UserSession | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    now = utcnow()
    if session is None or session.expires_at <= now:
        return None
    if not session.user.is_active:
        return None
    # Update activity at most every 5 minutes to avoid a write on every request.
    if now - session.last_seen_at > timedelta(minutes=5):
        session.last_seen_at = now
        session.user.last_active_at = now
        db.commit()
    return session


def get_optional_user(request: Request, db: DbSession) -> User | None:
    session = _load_session(request, db)
    if session is None:
        return None
    request.state.session = session
    return session.user


def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    if user is None:
        raise AuthenticationError("Log in om verder te gaan.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_roles(*roles: UserRole):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("Je hebt geen toegang tot deze functie.")
        return user

    return checker


CandidateUser = Annotated[User, Depends(require_roles(UserRole.CANDIDATE))]
EmployerUser = Annotated[User, Depends(require_roles(UserRole.EMPLOYER, UserRole.ADMIN))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def verify_csrf(request: Request, db: DbSession) -> None:
    """CSRF protection for state-changing requests: double-submit token (header must equal the
    tf_csrf cookie, which for logged-in users is bound to the session) plus an Origin check."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    settings = get_settings()
    origin = request.headers.get("origin")
    allowed = {settings.frontend_url.rstrip("/"), *(o.rstrip("/") for o in settings.cors_origin_list)}
    if origin and origin.rstrip("/") not in allowed and settings.app_env != "test":
        raise PermissionDeniedError("Ongeldige herkomst van het verzoek.", code="csrf_failed")
    header = request.headers.get(CSRF_HEADER, "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    if not header or not cookie or not secrets.compare_digest(header, cookie):
        raise PermissionDeniedError("Je sessie is verlopen. Vernieuw de pagina en probeer opnieuw.", code="csrf_failed")
    session = _load_session(request, db)
    if session is not None and not secrets.compare_digest(header, session.csrf_token):
        raise PermissionDeniedError("Je sessie is verlopen. Vernieuw de pagina en probeer opnieuw.", code="csrf_failed")
