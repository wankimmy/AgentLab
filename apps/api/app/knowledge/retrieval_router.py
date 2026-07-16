import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent_versions.router import _get_version
from app.agents.router import _get_user_agent
from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import AgentVersion, AgentVersionCollection, KnowledgeCollection
from app.schemas.knowledge import (
    RetrievalDebugChunk,
    RetrievalDebugRequest,
    RetrievalDebugResponse,
    VersionCollectionsResponse,
    VersionCollectionsUpdate,
    VersionRagUpdate,
)
from app.schemas.tools import VersionToolsUpdate
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/knowledge/retrieval", tags=["knowledge-retrieval"])
version_router = APIRouter(prefix="/agents/{agent_id}/versions", tags=["agent-version-collections"])


@router.post("/debug", response_model=RetrievalDebugResponse)
def retrieval_debug(
    body: RetrievalDebugRequest, user: CurrentUser, db: Session = Depends(get_db)
) -> RetrievalDebugResponse:
    if body.agent_version_id:
        version = db.get(AgentVersion, body.agent_version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Agent version not found")
        agent = _get_user_agent(version.agent_id, user, db)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        config = body.retrieval_config or version.retrieval_config
        collection_ids = body.collection_ids or None
        chunks = RetrievalService(db).retrieve(
            body.query,
            version_id=version.id,
            collection_ids=collection_ids,
            config=config,
        )
        mode = config.get("mode", config.get("search_mode", "hybrid"))
    else:
        if not body.collection_ids:
            raise HTTPException(
                status_code=400,
                detail="Provide agent_version_id or collection_ids",
            )
        owned = (
            db.query(KnowledgeCollection.id)
            .filter(
                KnowledgeCollection.user_id == user.id,
                KnowledgeCollection.id.in_(body.collection_ids),
            )
            .count()
        )
        if owned != len(body.collection_ids):
            raise HTTPException(status_code=404, detail="Collection not found")
        config = body.retrieval_config
        chunks = RetrievalService(db).retrieve(
            body.query,
            collection_ids=body.collection_ids,
            config=config,
        )
        mode = config.get("mode", config.get("search_mode", "hybrid"))

    return RetrievalDebugResponse(
        query=body.query,
        mode=str(mode),
        chunks=[
            RetrievalDebugChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_name=c.document_name,
                score=c.score,
                heading=c.heading,
                page_number=c.page_number,
                excerpt=c.excerpt,
                content=c.content,
            )
            for c in chunks
        ],
    )


@version_router.get("/{version_id}/collections", response_model=VersionCollectionsResponse)
def get_version_collections(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> VersionCollectionsResponse:
    _get_version(agent_id, version_id, user, db)
    rows = (
        db.query(AgentVersionCollection.collection_id)
        .filter(AgentVersionCollection.agent_version_id == version_id)
        .all()
    )
    return VersionCollectionsResponse(
        agent_version_id=version_id,
        collection_ids=[row[0] for row in rows],
    )


@version_router.put("/{version_id}/collections", response_model=VersionCollectionsResponse)
def put_version_collections(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    body: VersionCollectionsUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> VersionCollectionsResponse:
    _get_version(agent_id, version_id, user, db)
    owned = (
        db.query(KnowledgeCollection)
        .filter(
            KnowledgeCollection.user_id == user.id,
            KnowledgeCollection.id.in_(body.collection_ids),
        )
        .count()
    )
    if owned != len(set(body.collection_ids)):
        raise HTTPException(status_code=404, detail="One or more collections not found")

    db.query(AgentVersionCollection).filter(
        AgentVersionCollection.agent_version_id == version_id
    ).delete()
    for cid in set(body.collection_ids):
        db.add(AgentVersionCollection(agent_version_id=version_id, collection_id=cid))
    db.commit()
    return VersionCollectionsResponse(
        agent_version_id=version_id,
        collection_ids=list(set(body.collection_ids)),
    )


@version_router.patch("/{version_id}/rag", response_model=dict)
def patch_version_rag(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    body: VersionRagUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    version = _get_version(agent_id, version_id, user, db)
    if body.rag_enabled is not None:
        version.rag_enabled = body.rag_enabled
    if body.retrieval_config is not None:
        version.retrieval_config = body.retrieval_config
    db.commit()
    return {
        "rag_enabled": version.rag_enabled,
        "retrieval_config": version.retrieval_config,
    }


@version_router.patch("/{version_id}/tools", response_model=dict)
def patch_version_tools(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    body: VersionToolsUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    version = _get_version(agent_id, version_id, user, db)
    version.tool_config = body.tool_config
    db.commit()
    return {"tool_config": version.tool_config}
