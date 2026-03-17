from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Draft
from app.schemas.draft import DraftOut, DraftUpdate
from app.core.exceptions import DraftNotFoundError

router = APIRouter()


@router.get("/drafts/{draft_id}", response_model=DraftOut)
async def get_draft(draft_id: int, db: AsyncSession = Depends(get_db)):
    draft = await db.get(Draft, draft_id)
    if not draft:
        raise DraftNotFoundError(draft_id)
    return draft


@router.patch("/drafts/{draft_id}", response_model=DraftOut)
async def update_draft(
    draft_id: int,
    update: DraftUpdate,
    db: AsyncSession = Depends(get_db),
):
    draft = await db.get(Draft, draft_id)
    if not draft:
        raise DraftNotFoundError(draft_id)

    if update.post_text is not None:
        draft.post_text = update.post_text
        draft.character_count = len(update.post_text)
    if update.selected_image_url is not None:
        draft.selected_image_url = update.selected_image_url

    await db.commit()
    await db.refresh(draft)
    return draft


@router.get("/drafts", response_model=list[DraftOut])
async def list_drafts(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Draft)
        .where(Draft.session_id == session_id)
        .order_by(Draft.created_at.desc())
        .limit(20)
    )
    return result.scalars().all()
