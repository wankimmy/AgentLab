import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import SampleDataPack
from app.sample_packs.erp_install import install_erp_pack
from app.schemas.common import SamplePackInstallResponse, SamplePackSummary
from app.services.template_service import create_agent_from_template, get_template_by_slug

router = APIRouter(prefix="/sample-packs", tags=["sample-packs"])


@router.get("", response_model=list[SamplePackSummary])
def list_sample_packs(user: CurrentUser, db: Session = Depends(get_db)) -> list[SamplePackSummary]:
    packs = db.query(SampleDataPack).order_by(SampleDataPack.name).all()
    return [SamplePackSummary.model_validate(p) for p in packs]


@router.post(
    "/{pack_id}/install",
    response_model=SamplePackInstallResponse,
    status_code=status.HTTP_201_CREATED,
)
def install_sample_pack(
    pack_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> SamplePackInstallResponse:
    pack = db.get(SampleDataPack, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Sample pack not found")
    if not pack.template_slug:
        raise HTTPException(status_code=400, detail="Sample pack has no linked template")

    template = get_template_by_slug(db, pack.template_slug)
    if not template:
        raise HTTPException(status_code=404, detail="Linked template not found")

    synthetic_label = pack.manifest.get("label", "SYNTHETIC DATA")

    if pack.slug == "erp-support":
        result = install_erp_pack(
            db,
            user,
            template.id,
            pack_name=pack.name,
            pack_slug=pack.slug,
            synthetic_label=synthetic_label,
        )
        db.commit()
        return SamplePackInstallResponse(
            agent_id=result["agent_id"],
            message=(
                f"Installed {pack.name}: agent, {result['knowledge_doc_count']} knowledge docs, "
                f"{result['eval_case_count']} eval cases (synthetic)."
            ),
            collection_id=result["collection_id"],
            dataset_id=result["dataset_id"],
            eval_case_count=result["eval_case_count"],
            knowledge_doc_count=result["knowledge_doc_count"],
        )

    agent = create_agent_from_template(
        db,
        user,
        template.id,
        name=pack.name,
        purpose=f"Synthetic demo agent from {pack.slug} sample pack.",
        notes=f"{synthetic_label}: installed from sample pack {pack.slug}.",
    )
    return SamplePackInstallResponse(
        agent_id=agent.id,
        message=f"Installed {pack.name}. Agent created with synthetic data label.",
    )
