"""CV quality analysis.

The quality score is a transparent, rule-based checklist (each check is shown to the user); a language
model only adds written strengths and suggestions when one is configured. No score is shown before an
analysis has run."""

import uuid

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.integrations.ai.base import AIError
from app.integrations.ai.factory import llm_configured
from app.integrations.ai.prompts import CV_ANALYSIS
from app.models.entities import CandidateProfile, CVAnalysis, User
from app.schemas.profile import ProfileContent
from app.services import ai_service


class AIFeedback(BaseModel):
    strengths: list[str] = Field(default_factory=list, max_length=6)
    suggestions: list[str] = Field(default_factory=list, max_length=8)


def rule_checks(profile: CandidateProfile, user: User) -> list[dict]:
    content = ProfileContent.model_validate(profile.content or {})
    bullets = [b for e in content.experiences for b in e.bullets]
    summary_words = len((profile.summary or "").split())
    quantified = sum(1 for b in bullets if any(ch.isdigit() for ch in b))
    dated = sum(1 for e in content.experiences if e.start)
    checks = [
        (
            "contact",
            bool(profile.phone or user.email) and bool(profile.city),
            10,
            {"phone": bool(profile.phone), "city": bool(profile.city)},
        ),
        ("headline", bool(profile.headline), 5, {}),
        ("summary", 30 <= summary_words <= 150, 15, {"words": summary_words}),
        ("experience", len(content.experiences) >= 1, 15, {"count": len(content.experiences)}),
        (
            "experience_dates",
            bool(content.experiences) and dated == len(content.experiences),
            10,
            {"dated": dated, "count": len(content.experiences)},
        ),
        ("bullets", bool(content.experiences) and all(len(e.bullets) >= 2 for e in content.experiences), 10, {"total": len(bullets)}),
        ("quantified", quantified >= 2, 10, {"count": quantified}),
        ("skills", len(content.skills) >= 6, 10, {"count": len(content.skills)}),
        ("education", len(content.education) >= 1, 10, {"count": len(content.education)}),
        ("languages", len(content.languages) >= 1, 5, {"count": len(content.languages)}),
    ]
    return [{"key": k, "passed": p, "weight": w, "detail": d} for k, p, w, d in checks]


def run_analysis(db: Session, user: User, profile: CandidateProfile, cv_document_id: uuid.UUID | None, cv_text: str | None) -> CVAnalysis:
    checks = rule_checks(profile, user)
    score = round(sum(c["weight"] for c in checks if c["passed"]) / sum(c["weight"] for c in checks) * 100)
    analysis = CVAnalysis(user_id=user.id, cv_document_id=cv_document_id, method="rule_based", quality_score=score, checks=checks)
    if llm_configured() and (cv_text or profile.content):
        source = cv_text or ProfileContent.model_validate(profile.content).model_dump_json()
        try:
            feedback, provider, model = ai_service.generate(
                db,
                user_id=user.id,
                operation="cv_analysis",
                system=CV_ANALYSIS,
                user=f"<document>\n{source[:12000]}\n</document>",
                schema=AIFeedback,
                temperature=0.3,
            )
            analysis.strengths = feedback.strengths
            analysis.suggestions = feedback.suggestions
            analysis.method = "rule_based+ai"
            analysis.provider, analysis.model = provider, model
        except AIError:
            analysis.status = "completed_without_ai"
    db.add(analysis)
    db.commit()
    return analysis
