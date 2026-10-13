"""Career assistant. The context only ever contains the requesting user's own profile and vacancies the
user may see; other users' data is never loaded, so prompt manipulation cannot reach it."""

import json
import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.rate_limit import rate_limiter
from app.integrations.ai.base import ChatMessage
from app.integrations.ai.prompts import CAREER_ASSISTANT
from app.models.entities import AssistantMessage, User
from app.models.enums import JobStatus
from app.schemas.profile import ProfileContent
from app.services import ai_service
from app.services.candidate_service import get_preferences, get_profile
from app.services.job_service import get_visible_job
from app.services.matching import service as matching

HISTORY_LIMIT = 12


def _context(db: Session, user: User, job_ids: list[uuid.UUID]) -> str:
    profile = get_profile(db, user.id)
    prefs = get_preferences(db, user.id)
    content = ProfileContent.model_validate(profile.content or {})
    profile_data = {
        "name": user.full_name,
        "headline": profile.headline,
        "summary": profile.summary,
        "city": profile.city,
        "experiences": [
            {"title": e.title, "employer": e.employer, "start": e.start, "end": e.end, "current": e.is_current, "bullets": e.bullets[:6]}
            for e in content.experiences[:8]
        ],
        "education": [{"degree": e.degree, "institution": e.institution} for e in content.education],
        "skills": content.skills,
        "languages": [lang.model_dump() for lang in content.languages],
        "desired_titles": prefs.desired_titles,
        "preferred_locations": prefs.preferred_locations,
    }
    vacancies = []
    for job_id in job_ids[:3]:
        job = get_visible_job(db, user, job_id)
        entry: dict[str, Any] = {
            "id": str(job.id),
            "title": job.title,
            "company": job.company.name,
            "city": job.city,
            "remote": job.remote_policy.value,
            "description": job.description[:3000],
            "responsibilities": job.responsibilities,
            "qualifications": job.qualifications,
            "required_skills": [s.name for s in job.skills if s.is_required],
            "preferred_skills": [s.name for s in job.skills if not s.is_required],
            "salary": {"min": job.salary_min, "max": job.salary_max, "period": job.salary_period.value if job.salary_period else None},
        }
        if job.status == JobStatus.PUBLISHED:
            match = matching.get_or_compute(db, user, [job])[job.id]
            entry["platform_match"] = {
                "score": match.score,
                "matching_skills": [s["name"] for s in match.result.get("matching_skills", [])],
                "missing_required_skills": [s["name"] for s in match.result.get("missing_required_skills", [])],
            }
        vacancies.append(entry)
    return (
        f"<profile>\n{json.dumps(profile_data, ensure_ascii=False)}\n</profile>\n"
        f"<vacancy>\n{json.dumps(vacancies, ensure_ascii=False)}\n</vacancy>"
    )


def history(db: Session, user: User) -> list[AssistantMessage]:
    rows = db.scalars(
        select(AssistantMessage).where(AssistantMessage.user_id == user.id).order_by(AssistantMessage.created_at.desc()).limit(50)
    )
    return list(reversed(list(rows)))


def ask(db: Session, user: User, message: str, job_ids: list[uuid.UUID]) -> AssistantMessage:
    rate_limiter.hit(f"assistant:{user.id}", limit=30, window_seconds=3600)
    if not message.strip():
        raise AppError("Typ eerst een vraag.", code="empty_message", status_code=422)
    context = _context(db, user, job_ids)
    previous = history(db, user)[-HISTORY_LIMIT:]
    messages = [ChatMessage(role=m.role, content=m.content) for m in previous]
    messages.append(ChatMessage(role="user", content=f"{context}\n\nVraag van de gebruiker:\n{message.strip()}"))
    reply = ai_service.chat(db, user_id=user.id, operation="assistant", system=CAREER_ASSISTANT, messages=messages)
    ids = [str(j) for j in job_ids[:3]]
    db.add(AssistantMessage(user_id=user.id, role="user", content=message.strip()[:4000], job_ids=ids))
    answer = AssistantMessage(user_id=user.id, role="assistant", content=reply.strip()[:8000], job_ids=ids)
    db.add(answer)
    db.commit()
    return answer


def clear(db: Session, user: User) -> None:
    db.execute(delete(AssistantMessage).where(AssistantMessage.user_id == user.id))
    db.commit()
