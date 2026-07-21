import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.exports.promptfoo import build_promptfoo_config, export_promptfoo_yaml
from app.models.entities import Agent, AgentVersion, EvaluationDataset

router = APIRouter(prefix="/exports", tags=["exports"])


class PromptfooExportRequest(BaseModel):
    dataset_id: uuid.UUID
    agent_version_id: uuid.UUID
    dataset_version_id: uuid.UUID | None = None
    format: str = "yaml"


@router.post("/promptfoo")
def export_promptfoo(
    body: PromptfooExportRequest, user: CurrentUser, db: Session = Depends(get_db)
) -> dict:
    dataset = (
        db.query(EvaluationDataset)
        .filter(EvaluationDataset.id == body.dataset_id, EvaluationDataset.user_id == user.id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    version = db.get(AgentVersion, body.agent_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Agent version not found")
    agent = db.get(Agent, version.agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent version not found")

    try:
        if body.format == "json":
            return build_promptfoo_config(
                db,
                dataset_id=body.dataset_id,
                agent_version_id=body.agent_version_id,
                dataset_version_id=body.dataset_version_id,
            )
        yaml_text = export_promptfoo_yaml(
            db,
            dataset_id=body.dataset_id,
            agent_version_id=body.agent_version_id,
            dataset_version_id=body.dataset_version_id,
        )
        return {"format": "yaml", "content": yaml_text}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
