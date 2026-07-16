from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import ModelRegistry
from app.schemas.common import ModelRegistryItem

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelRegistryItem])
def list_models(user: CurrentUser, db: Session = Depends(get_db)) -> list[ModelRegistryItem]:
    models = (
        db.query(ModelRegistry)
        .filter(ModelRegistry.active.is_(True))
        .order_by(ModelRegistry.provider, ModelRegistry.model)
        .all()
    )
    return [ModelRegistryItem.model_validate(m) for m in models]
