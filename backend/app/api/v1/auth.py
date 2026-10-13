import uuid

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from app.api.deps import CSRF_COOKIE, SESSION_COOKIE, CurrentUser, DbSession, client_ip
from app.core.config import get_settings
from app.core.rate_limit import rate_limiter
from app.core.security import new_token
from app.models.entities import UserSession
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionOut,
    UserOut,
    VerifyEmailRequest,
)
from app.schemas.common import Message
from app.services import auth_service
from app.services.users import user_out

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_args() -> dict:
    settings = get_settings()
    return {"secure": settings.is_production, "samesite": "lax", "domain": settings.cookie_domain, "path": "/"}


def _set_session_cookies(response: Response, token: str, csrf: str) -> None:
    max_age = get_settings().session_ttl_hours * 3600
    response.set_cookie(SESSION_COOKIE, token, httponly=True, max_age=max_age, **_cookie_args())
    # Readable by the frontend's JavaScript on purpose: it is echoed in the X-CSRF-Token header.
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, max_age=max_age, **_cookie_args())


@router.get("/csrf", response_model=Message, summary="Get a CSRF token cookie (call once before the first POST)")
def csrf(request: Request, response: Response) -> Message:
    if not request.cookies.get(CSRF_COOKIE):
        response.set_cookie(CSRF_COOKIE, new_token(), httponly=False, max_age=86400, **_cookie_args())
    return Message(message="ok")


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest, request: Request, response: Response, db: DbSession) -> UserOut:
    ip = client_ip(request)
    rate_limiter.hit(f"register:{ip}", limit=10, window_seconds=3600)
    user = auth_service.register(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        account_type=body.account_type,
        company_name=body.company_name,
        ip=ip,
    )
    token, csrf_token = auth_service.create_session(db, user, request.headers.get("user-agent"), ip)
    _set_session_cookies(response, token, csrf_token)
    return user_out(db, user)


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, request: Request, response: Response, db: DbSession) -> UserOut:
    ip = client_ip(request)
    rate_limiter.hit(f"login-ip:{ip}", limit=30, window_seconds=300)
    rate_limiter.hit(f"login-email:{body.email.lower()}", limit=8, window_seconds=300)
    user = auth_service.authenticate(db, body.email, body.password)
    token, csrf_token = auth_service.create_session(db, user, request.headers.get("user-agent"), ip)
    _set_session_cookies(response, token, csrf_token)
    return user_out(db, user)


@router.post("/logout", response_model=Message)
def logout(request: Request, response: Response, db: DbSession, user: CurrentUser) -> Message:
    session = getattr(request.state, "session", None)
    if session is not None:
        auth_service.end_session(db, session)
    response.delete_cookie(SESSION_COOKIE, **_cookie_args())
    response.delete_cookie(CSRF_COOKIE, **_cookie_args())
    return Message(message="Je bent uitgelogd.")


@router.get("/me", response_model=UserOut)
def me(db: DbSession, user: CurrentUser) -> UserOut:
    return user_out(db, user)


@router.post("/verify-email", response_model=UserOut)
def verify_email(body: VerifyEmailRequest, request: Request, db: DbSession) -> UserOut:
    rate_limiter.hit(f"verify:{client_ip(request)}", limit=20, window_seconds=300)
    return user_out(db, auth_service.verify_email(db, body.token))


@router.post("/resend-verification", response_model=Message)
def resend_verification(db: DbSession, user: CurrentUser) -> Message:
    rate_limiter.hit(f"resend:{user.id}", limit=3, window_seconds=3600)
    auth_service.send_verification(db, user)
    return Message(message="We hebben een nieuwe bevestigingsmail gestuurd.")


@router.post("/forgot-password", response_model=Message)
def forgot_password(body: ForgotPasswordRequest, request: Request, db: DbSession) -> Message:
    ip = client_ip(request)
    rate_limiter.hit(f"forgot-ip:{ip}", limit=10, window_seconds=3600)
    rate_limiter.hit(f"forgot-email:{body.email.lower()}", limit=3, window_seconds=3600)
    auth_service.request_password_reset(db, body.email, ip)
    return Message(message="Als er een account met dit e-mailadres bestaat, ontvang je zo een e-mail met een link.")


@router.post("/reset-password", response_model=Message)
def reset_password(body: ResetPasswordRequest, request: Request, db: DbSession) -> Message:
    ip = client_ip(request)
    rate_limiter.hit(f"reset:{ip}", limit=10, window_seconds=300)
    auth_service.reset_password(db, body.token, body.password, ip)
    return Message(message="Je wachtwoord is gewijzigd. Je kunt nu inloggen.")


@router.post("/change-password", response_model=Message)
def change_password(body: ChangePasswordRequest, request: Request, db: DbSession, user: CurrentUser) -> Message:
    rate_limiter.hit(f"change-pw:{user.id}", limit=5, window_seconds=300)
    auth_service.change_password(db, user, body.current_password, body.new_password, request.state.session.id)
    return Message(message="Je wachtwoord is gewijzigd. Andere apparaten zijn uitgelogd.")


@router.get("/sessions", response_model=list[SessionOut])
def sessions(request: Request, db: DbSession, user: CurrentUser) -> list[SessionOut]:
    current = request.state.session.id
    rows = db.scalars(select(UserSession).where(UserSession.user_id == user.id).order_by(UserSession.last_seen_at.desc()))
    return [SessionOut.model_validate(s).model_copy(update={"current": s.id == current}) for s in rows]


@router.delete("/sessions/{session_id}", response_model=Message)
def revoke_session(session_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Message:
    auth_service.revoke_session(db, user, session_id)
    return Message(message="De sessie is beëindigd.")
