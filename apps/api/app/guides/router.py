from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import Guide
from app.schemas.common import GuideDetail, GuideSectionItem, GuideSummary

router = APIRouter(prefix="/guides", tags=["guides"])


@router.get("", response_model=list[GuideSummary])
def list_guides(user: CurrentUser, db: Session = Depends(get_db)) -> list[GuideSummary]:
    guides = db.query(Guide).order_by(Guide.sort_order, Guide.title).all()
    return [
        GuideSummary(
            id=g.id,
            slug=g.slug,
            title=g.title,
            section=g.section.value,
            summary=g.summary,
            screen_link=g.screen_link,
        )
        for g in guides
    ]


@router.get("/{slug}", response_model=GuideDetail)
def get_guide(slug: str, user: CurrentUser, db: Session = Depends(get_db)) -> GuideDetail:
    guide = db.query(Guide).filter(Guide.slug == slug).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")
    return GuideDetail(
        id=guide.id,
        slug=guide.slug,
        title=guide.title,
        section=guide.section.value,
        summary=guide.summary,
        screen_link=guide.screen_link,
        sections=[
            GuideSectionItem(heading=s.heading, content=s.content)
            for s in sorted(guide.sections, key=lambda x: x.sort_order)
        ],
    )
