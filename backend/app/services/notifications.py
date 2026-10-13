import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.entities import Notification


def notify(db: Session, user_id: uuid.UUID, type_: str, title: str, body: str | None = None, link: str | None = None) -> None:
    db.add(Notification(user_id=user_id, type=type_, title=title, body=body, link=link))


def list_for(db: Session, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
    return list(
        db.scalars(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(limit))
    )


def unread_count(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None)))
        or 0
    )


def mark_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID | None = None) -> None:
    stmt = update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
    if notification_id:
        stmt = stmt.where(Notification.id == notification_id)
    db.execute(stmt.values(read_at=utcnow()))
