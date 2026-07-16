from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.entities import ModelPricing


def estimate_cost(
    db: Session,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    pricing = (
        db.query(ModelPricing)
        .filter(ModelPricing.provider == provider, ModelPricing.model == model)
        .order_by(ModelPricing.effective_from.desc())
        .first()
    )
    if not pricing:
        return Decimal("0")
    input_cost = Decimal(input_tokens) * pricing.input_token_cost
    output_cost = Decimal(output_tokens) * pricing.output_token_cost
    return input_cost + output_cost
