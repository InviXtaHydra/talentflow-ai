"""Aggregated, evidence-based dashboard data. Every number is counted from stored records."""

from collections import Counter
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.entities import (
    Application,
    ApplicationStatusHistory,
    CVAnalysis,
    CVDocument,
    CVVersion,
    Job,
    JobView,
    SavedJob,
    User,
)
from app.models.enums import ApplicationChannel, CVVersionKind, JobStatus
from app.services import job_service
from app.services.candidate_service import get_preferences, get_profile
from app.services.company_service import member_company_ids
from app.services.matching import service as matching
from app.utils import geo


def candidate_dashboard(db: Session, user: User) -> dict[str, Any]:
    profile = get_profile(db, user.id)
    prefs = get_preferences(db, user.id)
    recommended = matching.recommendations(db, user, limit=30)
    top = recommended[:6]

    latest_cv = db.scalar(select(CVDocument).where(CVDocument.user_id == user.id).order_by(CVDocument.created_at.desc()))
    latest_analysis = db.scalar(select(CVAnalysis).where(CVAnalysis.user_id == user.id).order_by(CVAnalysis.created_at.desc()))
    versions = (
        db.scalar(select(func.count()).select_from(CVVersion).where(CVVersion.user_id == user.id, CVVersion.kind != CVVersionKind.ORIGINAL))
        or 0
    )
    status_counts = dict(
        db.execute(select(Application.status, func.count()).where(Application.user_id == user.id).group_by(Application.status)).all()
    )

    # Career insights: derived from the best-matching published vacancies.
    missing = Counter(s["name"] for _, m in recommended for s in m.result.get("missing_required_skills", []))
    language_needs = Counter(code for job, _ in recommended for code in (job.required_languages or []))
    candidate_langs = {lang["code"] for lang in (profile.content or {}).get("languages", [])}
    insights: list[dict[str, Any]] = []
    for skill, count in missing.most_common(3):
        if count >= 2:
            insights.append({"type": "skill_gap", "skill": skill, "jobs": count, "sample": len(recommended)})
    for code, count in language_needs.items():
        if code not in candidate_langs and count >= 2:
            insights.append({"type": "language_gap", "language": code, "jobs": count, "sample": len(recommended)})
    if recommended:
        remote_share = sum(1 for job, _ in recommended if job.remote_policy.value in ("remote", "hybrid")) / len(recommended)
        insights.append({"type": "remote_share", "share": round(remote_share * 100), "sample": len(recommended)})
    total_published = db.scalar(select(func.count()).select_from(Job).where(Job.status == JobStatus.PUBLISHED)) or 0
    if prefs.preferred_locations:
        city_jobs = [
            j
            for j in db.scalars(select(Job).where(Job.status == JobStatus.PUBLISHED))
            if j.city
            and any(
                geo.same_place(j.city, p) or (geo.distance_km(j.city, p) or 999) <= (prefs.max_commute_km or 50)
                for p in prefs.preferred_locations
            )
        ]
        insights.append({"type": "jobs_in_area", "count": len(city_jobs), "total": total_published})

    # Recent activity, merged and sorted.
    activity: list[dict[str, Any]] = []
    for saved in db.scalars(select(SavedJob).where(SavedJob.user_id == user.id).order_by(SavedJob.created_at.desc()).limit(5)):
        activity.append({"type": "saved_job", "at": saved.created_at, "title": saved.job.title, "link": f"/jobs/{saved.job_id}"})
    for view in db.scalars(select(JobView).where(JobView.user_id == user.id).order_by(JobView.viewed_at.desc()).limit(5)):
        activity.append({"type": "viewed_job", "at": view.viewed_at, "title": view.job.title, "link": f"/jobs/{view.job_id}"})
    for version in db.scalars(select(CVVersion).where(CVVersion.user_id == user.id).order_by(CVVersion.created_at.desc()).limit(5)):
        link = f"/cv/optimizations/{version.id}" if version.kind == CVVersionKind.OPTIMIZED else f"/cv/versions/{version.id}"
        activity.append({"type": "cv_version", "at": version.created_at, "title": version.title, "link": link})
    history = db.execute(
        select(ApplicationStatusHistory, Application)
        .join(Application, Application.id == ApplicationStatusHistory.application_id)
        .where(Application.user_id == user.id)
        .order_by(ApplicationStatusHistory.created_at.desc())
        .limit(5)
    ).all()
    for entry, application in history:
        activity.append(
            {
                "type": "application",
                "at": entry.created_at,
                "title": application.job.title,
                "status": entry.to_status.value,
                "link": "/applications",
            }
        )
    activity.sort(key=lambda a: a["at"], reverse=True)

    return {
        "profile": {
            "headline": profile.headline,
            "confirmed": profile.confirmed_at is not None,
            "onboarding_completed": profile.onboarding_completed_at is not None,
            "has_content": bool((profile.content or {}).get("experiences") or (profile.content or {}).get("skills")),
        },
        "recommendations": [job_service.summary(job, match=m).model_dump(mode="json") for job, m in top],
        "recommendation_count": len(recommended),
        "cv": {
            "latest": None
            if latest_cv is None
            else {
                "id": str(latest_cv.id),
                "filename": latest_cv.original_filename,
                "status": latest_cv.extraction_status.value,
                "confirmed": latest_cv.confirmed_at is not None,
                "uploaded_at": latest_cv.created_at.isoformat(),
            },
            "analysis": None
            if latest_analysis is None
            else {
                "id": str(latest_analysis.id),
                "quality_score": latest_analysis.quality_score,
                "method": latest_analysis.method,
                "created_at": latest_analysis.created_at.isoformat(),
                "suggestions": latest_analysis.suggestions[:3],
                "failed_checks": [c["key"] for c in latest_analysis.checks if not c["passed"]][:4],
            },
            "generated_versions": versions,
        },
        "applications": {status.value: count for status, count in status_counts.items()},
        "insights": insights,
        "activity": [{**a, "at": a["at"].isoformat()} for a in activity[:10]],
    }


def employer_dashboard(db: Session, user: User) -> dict[str, Any]:
    company_ids = member_company_ids(db, user)
    jobs = list(db.scalars(select(Job).where(Job.company_id.in_(company_ids)))) if company_ids else []
    job_ids = [j.id for j in jobs]
    status_counts = Counter(j.status.value for j in jobs)
    applications = (
        list(db.scalars(select(Application).where(Application.job_id.in_(job_ids), Application.channel == ApplicationChannel.PLATFORM)))
        if job_ids
        else []
    )
    by_status = Counter(a.status.value for a in applications)
    per_job = Counter(a.job_id for a in applications)
    since = utcnow() - timedelta(days=29)
    days = Counter(a.applied_at.date().isoformat() for a in applications if a.applied_at and a.applied_at >= since)
    timeline = [
        {"date": (since + timedelta(days=i)).date().isoformat(), "count": days.get((since + timedelta(days=i)).date().isoformat(), 0)}
        for i in range(30)
    ]
    titles = {j.id: j.title for j in jobs}
    recent = sorted((a for a in applications if a.applied_at), key=lambda a: a.applied_at, reverse=True)[:6]  # type: ignore[arg-type,return-value]
    return {
        "companies": len(company_ids),
        "jobs": {"total": len(jobs), **{k: status_counts.get(k, 0) for k in ("draft", "published", "closed")}},
        "applications": {"total": len(applications), **dict(by_status)},
        "per_job": [{"job_id": str(jid), "title": titles[jid], "count": n} for jid, n in per_job.most_common(8)],
        "timeline": timeline,
        "recent": [
            {
                "id": str(a.id),
                "job_title": titles[a.job_id],
                "candidate_name": a.user.full_name,
                "status": a.status.value,
                "applied_at": a.applied_at.isoformat() if a.applied_at else None,
            }
            for a in recent
        ],
    }
