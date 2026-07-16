from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent_versions.router import router as versions_router
from app.agents.router import router as agents_router
from app.authentication.router import CurrentUser
from app.authentication.router import router as auth_router
from app.conversations.router import router as conversations_router
from app.core.db import get_db
from app.guides.router import router as guides_router
from app.knowledge.retrieval_router import router as retrieval_router
from app.knowledge.retrieval_router import version_router as version_collections_router
from app.knowledge.router import router as knowledge_router
from app.messages.router import router as messages_router
from app.models.entities import Agent, AgentVersion, OnboardingProgress, ReleaseStatus
from app.models_api.router import router as models_router
from app.onboarding.router import router as onboarding_router
from app.sample_packs.router import router as sample_packs_router
from app.schemas.common import DashboardResponse
from app.templates.router import router as templates_router
from app.tool_approvals.router import router as tool_approvals_router
from app.tools.router import router as tools_router
from app.traces.router import router as traces_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(agents_router)
api_router.include_router(versions_router)
api_router.include_router(templates_router)
api_router.include_router(onboarding_router)
api_router.include_router(guides_router)
api_router.include_router(sample_packs_router)
api_router.include_router(conversations_router)
api_router.include_router(messages_router)
api_router.include_router(traces_router)
api_router.include_router(models_router)
api_router.include_router(knowledge_router)
api_router.include_router(retrieval_router)
api_router.include_router(version_collections_router)
api_router.include_router(tools_router)
api_router.include_router(tool_approvals_router)


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


@api_router.get("/dashboard", response_model=DashboardResponse)
def dashboard(user: CurrentUser, db: Session = Depends(get_db)) -> DashboardResponse:
    total_agents = db.query(Agent).filter(Agent.user_id == user.id).count()
    active_versions = (
        db.query(Agent)
        .filter(Agent.user_id == user.id, Agent.active_version_id.isnot(None))
        .count()
    )
    draft_versions = (
        db.query(AgentVersion)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .filter(Agent.user_id == user.id, AgentVersion.release_status == ReleaseStatus.draft)
        .count()
    )
    progress = db.get(OnboardingProgress, user.id)
    onboarding_complete = progress.completed if progress else False
    return DashboardResponse(
        total_agents=total_agents,
        active_versions=active_versions,
        draft_versions=draft_versions,
        onboarding_complete=onboarding_complete,
    )
