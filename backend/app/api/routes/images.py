import uuid
import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Draft
from app.schemas.image import ImageListResponse, ImageResult
from app.services.image_service import get_images_for_post
from app.services.session_service import get_session_data
from app.config import get_settings
from app.core.exceptions import DraftNotFoundError

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.get("/images", response_model=ImageListResponse)
async def get_images(
    draft_id: int,
    session_id: str,
    search_query: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    draft = await db.get(Draft, draft_id)
    if not draft:
        raise DraftNotFoundError(draft_id)

    # Try in-memory session first; fall back to DB-persisted queries (survives backend restarts)
    image_prompts = await get_session_data(session_id, "image_prompts")
    if not image_prompts and draft.pexels_queries:
        try:
            image_prompts = json.loads(draft.pexels_queries)
        except Exception:
            image_prompts = []
    image_prompts = image_prompts or []
    logger.info(
        "GET /images draft_id=%s session_id=%s search_query=%r image_prompts=%r",
        draft_id, session_id[:8], search_query, image_prompts,
    )

    result = await get_images_for_post(
        topic=draft.topic,
        post_text=draft.post_text or draft.topic,
        image_prompts=image_prompts,
        search_query=search_query or None,
    )
    return result


@router.post("/images/upload", response_model=ImageResult)
async def upload_image(file: UploadFile = File(...)):
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, and WebP images are allowed.")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 5MB.")

    image_id = str(uuid.uuid4())
    storage_path = Path(settings.local_storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg"
    local_path = storage_path / f"{image_id}.{ext}"
    local_path.write_bytes(contents)

    return ImageResult(
        id=image_id,
        url=f"/storage/{image_id}.{ext}",
        thumbnail_url=f"/storage/{image_id}.{ext}",
        source="uploaded",
    )
