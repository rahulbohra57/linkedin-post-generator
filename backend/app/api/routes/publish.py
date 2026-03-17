import httpx
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Draft, User, PublishedPost
from app.schemas.publish import PublishRequest, PublishResult
from app.services.linkedin_service import upload_image_to_linkedin, create_linkedin_post
from app.core.exceptions import DraftNotFoundError, LinkedInAuthError, LinkedInPublishError
from app.config import get_settings

settings = get_settings()
router = APIRouter()


@router.post("/publish", response_model=PublishResult)
async def publish_post(req: PublishRequest, db: AsyncSession = Depends(get_db)):
    # Fetch draft
    draft = await db.get(Draft, req.draft_id)
    if not draft:
        raise DraftNotFoundError(req.draft_id)

    if not draft.post_text:
        return PublishResult(success=False, error="Post text is empty.")

    # Fetch user + LinkedIn credentials
    result = await db.execute(select(User).where(User.session_id == req.session_id))
    user = result.scalar_one_or_none()

    if not user or not user.linkedin_access_token:
        raise LinkedInAuthError("LinkedIn account not connected. Please connect first.")

    access_token = user.linkedin_access_token
    linkedin_urn = user.linkedin_urn

    # Upload image if provided
    asset_urn = None
    image_url = req.image_url or draft.selected_image_url
    if image_url:
        try:
            if image_url.startswith("/storage/"):
                local_path = Path(settings.local_storage_path) / image_url.split("/storage/")[-1]
                image_bytes = local_path.read_bytes()
            else:
                async with httpx.AsyncClient() as client:
                    img_resp = await client.get(image_url, timeout=15.0)
                    image_bytes = img_resp.content

            asset_urn = await upload_image_to_linkedin(access_token, linkedin_urn, image_bytes)
        except Exception as e:
            # Non-fatal: post without image
            pass

    # Create the post
    post_data = await create_linkedin_post(
        access_token=access_token,
        linkedin_urn=linkedin_urn,
        post_text=draft.post_text,
        asset_urn=asset_urn,
    )

    # Save to DB
    published = PublishedPost(
        user_id=user.id,
        draft_id=draft.id,
        linkedin_post_id=post_data["post_id"],
        linkedin_post_url=post_data["post_url"],
    )
    db.add(published)
    draft.status = "published"
    await db.commit()

    return PublishResult(
        success=True,
        linkedin_post_url=post_data["post_url"],
        linkedin_post_id=post_data["post_id"],
        published_at=datetime.utcnow(),
    )
