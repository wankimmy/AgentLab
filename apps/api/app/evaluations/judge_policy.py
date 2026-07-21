from fastapi import HTTPException

from app.models.entities import EvalMode


def resolve_judge_enabled(mode: EvalMode, requested: bool | None) -> bool:
    if mode == EvalMode.release:
        if requested is False:
            raise HTTPException(status_code=400, detail="Judge is required for release mode")
        return True
    if mode == EvalMode.standard:
        if requested is None:
            return True
        return requested
    if requested is None:
        return False
    return requested
