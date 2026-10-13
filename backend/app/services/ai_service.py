"""Runs AI calls and records operational usage metadata (never prompts or responses)."""

import logging
import time
import uuid
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.integrations.ai.base import AIError, ChatMessage
from app.integrations.ai.factory import get_llm
from app.models.entities import AIUsageRecord

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("talentflow.ai")


def _record(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    operation: str,
    provider: str,
    model: str,
    duration_ms: int,
    success: bool,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    error_code: str | None = None,
) -> None:
    db.add(
        AIUsageRecord(
            user_id=user_id,
            operation=operation,
            provider=provider,
            model=model,
            duration_ms=duration_ms,
            success=success,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            error_code=error_code,
        )
    )
    db.flush()


def generate(
    db: Session, *, user_id: uuid.UUID | None, operation: str, system: str, user: str, schema: type[T], temperature: float = 0.2
) -> tuple[T, str, str]:
    """Returns (validated result, provider name, model name)."""
    llm = get_llm()
    started = time.monotonic()
    try:
        result, usage = llm.generate_structured(system=system, user=user, schema=schema, temperature=temperature)
    except AIError as exc:
        _record(
            db,
            user_id=user_id,
            operation=operation,
            provider=llm.name,
            model=llm.model,
            duration_ms=int((time.monotonic() - started) * 1000),
            success=False,
            error_code=exc.code,
        )
        logger.warning("AI %s failed: %s", operation, exc.code)
        raise
    _record(
        db,
        user_id=user_id,
        operation=operation,
        provider=usage.provider,
        model=usage.model,
        duration_ms=usage.duration_ms,
        success=True,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
    )
    return result, usage.provider, usage.model


def chat(db: Session, *, user_id: uuid.UUID, operation: str, system: str, messages: list[ChatMessage]) -> str:
    llm = get_llm()
    started = time.monotonic()
    try:
        reply, usage = llm.chat(system=system, messages=messages)
    except AIError as exc:
        _record(
            db,
            user_id=user_id,
            operation=operation,
            provider=llm.name,
            model=llm.model,
            duration_ms=int((time.monotonic() - started) * 1000),
            success=False,
            error_code=exc.code,
        )
        raise
    _record(
        db,
        user_id=user_id,
        operation=operation,
        provider=usage.provider,
        model=usage.model,
        duration_ms=usage.duration_ms,
        success=True,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
    )
    return reply
