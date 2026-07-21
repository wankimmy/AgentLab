"""Full ERP sample pack installation."""

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.knowledge.pipeline import process_document_sync
from app.models.entities import (
    Agent,
    AgentVersion,
    AgentVersionCollection,
    CaseStatus,
    Document,
    DocumentStatus,
    EvaluationCase,
    EvaluationDataset,
    EvaluationDatasetVersion,
    KnowledgeCollection,
    ReadinessStatus,
    User,
)
from app.sample_packs.erp_fixtures import ERP_EVAL_CASES_25, ERP_KNOWLEDGE_DOCS
from app.services.template_service import create_agent_from_template


def _create_text_document(db: Session, collection_id: uuid.UUID, filename: str, content: str) -> Document:
    document = Document(
        collection_id=collection_id,
        filename=filename,
        content_type="text/markdown",
        storage_path="",
        status=DocumentStatus.uploaded,
    )
    db.add(document)
    db.flush()
    upload_dir = Path(settings.uploads_dir) / str(collection_id) / str(document.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    dest.write_text(content, encoding="utf-8")
    document.storage_path = str(dest)
    db.flush()
    process_document_sync(document.id)
    db.refresh(document)
    return document


def install_erp_pack(
    db: Session,
    user: User,
    template_id: uuid.UUID,
    *,
    pack_name: str,
    pack_slug: str,
    synthetic_label: str,
) -> dict:
    agent = create_agent_from_template(
        db,
        user,
        template_id,
        name=pack_name,
        purpose=f"Synthetic demo agent from {pack_slug} sample pack.",
        notes=f"{synthetic_label}: installed from sample pack {pack_slug}.",
    )
    db.refresh(agent)
    version = db.get(AgentVersion, agent.active_version_id)

    collection = KnowledgeCollection(
        user_id=user.id,
        name=f"{pack_name} Knowledge (synthetic)",
        description="Synthetic ERP manuals for demo and evaluation.",
        purpose="ERP support grounding",
        readiness_status=ReadinessStatus.ready_for_testing,
        planning_metadata={"synthetic": True, "source": pack_slug},
    )
    db.add(collection)
    db.flush()

    for doc in ERP_KNOWLEDGE_DOCS:
        body = f"# {doc['title']}\n\n{doc['content']}"
        _create_text_document(db, collection.id, doc["filename"], body)

    if version:
        db.add(AgentVersionCollection(agent_version_id=version.id, collection_id=collection.id))

    dataset = EvaluationDataset(
        user_id=user.id,
        agent_id=agent.id,
        name=f"{pack_name} Evaluation Set",
        description="25 synthetic cases covering correct, unsupported, citation, tool, and security.",
    )
    db.add(dataset)
    db.flush()
    dv = EvaluationDatasetVersion(dataset_id=dataset.id, version_number=1)
    db.add(dv)
    db.flush()

    for row in ERP_EVAL_CASES_25:
        status_raw = row.get("status", "approved")
        status = CaseStatus.draft if status_raw == "draft" else CaseStatus.approved
        db.add(
            EvaluationCase(
                dataset_version_id=dv.id,
                name=row["name"],
                category=row.get("category", ""),
                user_message=row["user_message"],
                expected_source=row.get("expected_source"),
                expected_citation=row.get("expected_citation"),
                status=status,
            )
        )

    db.flush()
    return {
        "agent_id": agent.id,
        "collection_id": collection.id,
        "dataset_id": dataset.id,
        "dataset_version_id": dv.id,
        "knowledge_doc_count": len(ERP_KNOWLEDGE_DOCS),
        "eval_case_count": len(ERP_EVAL_CASES_25),
    }
