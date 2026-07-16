import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AgentVersion
from app.services.retrieval_service import RetrievalService


def search_knowledge(
    db: Session,
    version: AgentVersion,
    query: str,
    collection_id: str | None = None,
) -> dict[str, Any]:
    config = version.retrieval_config or {}
    collection_ids = None
    if collection_id:
        collection_ids = [uuid.UUID(collection_id)]
    chunks = RetrievalService(db).retrieve(
        query,
        version_id=version.id,
        collection_ids=collection_ids,
        config=config,
    )
    return {
        "query": query,
        "results": [
            {
                "chunk_id": str(c.chunk_id),
                "document_name": c.document_name,
                "excerpt": c.excerpt,
                "score": c.score,
                "heading": c.heading,
            }
            for c in chunks
        ],
    }
