from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import get_settings
from app.integrations.ai.factory import get_embeddings, llm_configured

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness: the API process is running")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness: database reachable, AI configuration")
def ready(db: DbSession) -> JSONResponse:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    body = {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "ai": {
            "provider": settings.ai_provider,
            "configured": llm_configured(),
            "model": settings.ai_model if llm_configured() else None,
            "embeddings": get_embeddings() is not None,
        },
    }
    return JSONResponse(body, status_code=200 if database == "ok" else 503)


@router.get("/config", summary="Public, non-secret configuration for the frontend")
def public_config() -> dict:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "ai_configured": llm_configured(),
        "ai_provider": settings.ai_provider if llm_configured() else None,
        "ai_is_local": settings.ai_provider == "ollama",
        "max_upload_mb": settings.max_upload_mb,
        "environment": settings.app_env,
    }
