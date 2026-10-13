import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import CSRF_COOKIE, SESSION_COOKIE, CandidateUser, CurrentUser, DbSession
from app.api.v1.auth import _cookie_args
from app.db.base import utcnow
from app.schemas.auth import DeleteAccountRequest, UpdateAccountRequest, UserOut
from app.schemas.common import Message
from app.services import assistant_service, notifications, privacy_service, tasks
from app.services.users import user_out

router = APIRouter(tags=["account"])


@router.patch("/account", response_model=UserOut)
def update_account(body: UpdateAccountRequest, db: DbSession, user: CurrentUser) -> UserOut:
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.locale is not None:
        user.locale = body.locale
    if body.ai_processing_consent is not None:
        user.ai_processing_consent_at = utcnow() if body.ai_processing_consent else None
    db.commit()
    return user_out(db, user)


@router.get("/account/export", summary="Download all personal data (JSON)")
def export(db: DbSession, user: CurrentUser) -> Response:
    data = privacy_service.export_data(db, user)
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="talentflow-gegevens.json"', "Cache-Control": "no-store"},
    )


@router.post("/account/delete", response_model=Message, summary="Permanently delete the account and all personal data")
def delete_account(body: DeleteAccountRequest, response: Response, db: DbSession, user: CurrentUser) -> Message:
    privacy_service.delete_account(db, user, body.password)
    response.delete_cookie(SESSION_COOKIE, **_cookie_args())
    response.delete_cookie(CSRF_COOKIE, **_cookie_args())
    return Message(message="Je account en al je gegevens zijn verwijderd.")


# ── notifications ────────────────────────────────────────────────────────────


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    link: str | None
    read_at: datetime | None
    created_at: datetime


@router.get("/notifications", response_model=list[NotificationOut], tags=["notifications"])
def list_notifications(db: DbSession, user: CurrentUser) -> list[NotificationOut]:
    return [NotificationOut.model_validate(n, from_attributes=True) for n in notifications.list_for(db, user.id)]


@router.get("/notifications/unread-count", tags=["notifications"])
def unread(db: DbSession, user: CurrentUser) -> dict:
    return {"count": notifications.unread_count(db, user.id)}


@router.post("/notifications/read", response_model=Message, tags=["notifications"])
def read_all(db: DbSession, user: CurrentUser, notification_id: uuid.UUID | None = None) -> Message:
    notifications.mark_read(db, user.id, notification_id)
    db.commit()
    return Message(message="ok")


# ── background task status ───────────────────────────────────────────────────


class TaskOut(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    progress: int
    progress_message: str | None
    error_code: str | None
    error_message: str | None
    result: dict | None
    created_at: datetime
    finished_at: datetime | None


@router.get("/tasks/{task_id}", response_model=TaskOut, tags=["tasks"])
def task_status(task_id: uuid.UUID, db: DbSession, user: CurrentUser) -> TaskOut:
    task = tasks.get_for_user(db, task_id, user.id)
    return TaskOut(
        id=task.id,
        type=task.type,
        status=task.status.value,
        progress=task.progress,
        progress_message=task.progress_message,
        error_code=task.error_code,
        error_message=task.error_message,
        result=task.result,
        created_at=task.created_at,
        finished_at=task.finished_at,
    )


@router.post("/tasks/{task_id}/cancel", response_model=Message, tags=["tasks"])
def cancel_task(task_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Message:
    task = tasks.get_for_user(db, task_id, user.id)
    tasks.cancel(db, task)
    return Message(
        message="Geannuleerd." if task.status.value == "cancelled" else "Deze taak is al gestart en kan niet meer geannuleerd worden."
    )


# ── assistant ────────────────────────────────────────────────────────────────


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    job_ids: list[uuid.UUID] = Field(default_factory=list, max_length=3)


class AssistantMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    job_ids: list[str]
    created_at: datetime


@router.get("/assistant/messages", response_model=list[AssistantMessageOut], tags=["assistant"])
def assistant_history(db: DbSession, user: CandidateUser) -> list[AssistantMessageOut]:
    return [AssistantMessageOut.model_validate(m, from_attributes=True) for m in assistant_service.history(db, user)]


@router.post("/assistant/messages", response_model=AssistantMessageOut, tags=["assistant"])
def assistant_ask(body: AssistantRequest, request: Request, db: DbSession, user: CandidateUser) -> AssistantMessageOut:
    return AssistantMessageOut.model_validate(assistant_service.ask(db, user, body.message, body.job_ids), from_attributes=True)


@router.delete("/assistant/messages", response_model=Message, tags=["assistant"])
def assistant_clear(db: DbSession, user: CandidateUser) -> Message:
    assistant_service.clear(db, user)
    return Message(message="Gesprek gewist.")
