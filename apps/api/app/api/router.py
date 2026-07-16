from fastapi import APIRouter

from app.agent_versions.router import router as versions_router
from app.agents.router import router as agents_router
from app.authentication.router import router as auth_router
from app.templates.router import router as templates_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(agents_router)
api_router.include_router(versions_router)
api_router.include_router(templates_router)


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get("/ready")
def ready() -> dict[str, str | bool]:
    from sqlalchemy import text

    from app.core.db import SessionLocal
    from app.core.session import ping_redis

    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
    redis_ok = ping_redis()
    status = "ok" if db_ok and redis_ok else "degraded"
    return {"status": status, "database": db_ok, "redis": redis_ok}


@api_router.get("/dashboard")
def dashboard() -> dict:
    return {
        "total_agents": 0,
        "active_versions": 0,
        "draft_versions": 0,
        "latest_pass_rate": None,
        "latest_release_status": None,
        "recent_regressions": 0,
        "recent_failed_cases": 0,
        "avg_latency_ms": None,
        "p95_latency_ms": None,
        "recent_token_usage": 0,
        "estimated_cost": 0.0,
        "knowledge_status": "not_started",
        "background_jobs_pending": 0,
    }
