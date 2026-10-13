import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import anonymize_ip
from app.models.entities import AuditLog


def audit(
    db: Session,
    action: str,
    *,
    actor_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | str | None = None,
    ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Record a security-relevant event. `details` must not contain personal data or document contents."""
    db.add(
        AuditLog(
            actor_user_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            ip_hash=anonymize_ip(ip),
            details=details or {},
        )
    )
