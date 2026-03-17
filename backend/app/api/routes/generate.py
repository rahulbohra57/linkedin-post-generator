import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.generate import GenerateRequest, GenerateResponse
from app.db.database import get_db
from app.db.models import Draft, User
from app.agents.crew import run_pipeline
from app.services.session_service import set_session_data

router = APIRouter()


async def _run_and_save(
    draft_id: int,
    session_id: str,
    topic: str,
    tone: str,
    target_audience: str,
    post_length: str,
):
    """Background task: run pipeline, then update the draft in DB."""
    from app.db.database import AsyncSessionLocal

    try:
        result = await run_pipeline(session_id, topic, tone, target_audience, post_length)

        # Persist image prompts to session for image endpoint
        await set_session_data(session_id, "image_prompts", result.get("image_prompts", []))

        async with AsyncSessionLocal() as db:
            draft = await db.get(Draft, draft_id)
            if draft:
                draft.post_text = result["post_text"]
                draft.hashtags = result["hashtags"]
                draft.quality_score = result["quality_score"]
                draft.quality_notes = "\n".join(result.get("quality_notes", []))
                draft.character_count = result["character_count"]
                draft.status = "ready"
                await db.commit()
    except Exception as exc:
        async with AsyncSessionLocal() as db:
            draft = await db.get(Draft, draft_id)
            if draft:
                draft.status = "error"
                await db.commit()
        raise exc


@router.post("/generate", response_model=GenerateResponse)
async def generate_post(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Get or create user by session_id
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.session_id == req.session_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(session_id=req.session_id)
        db.add(user)
        await db.flush()

    # Create draft record
    draft = Draft(
        user_id=user.id,
        session_id=req.session_id,
        topic=req.topic,
        tone=req.tone,
        target_audience=req.target_audience,
        status="generating",
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    background_tasks.add_task(
        _run_and_save,
        draft.id,
        req.session_id,
        req.topic,
        req.tone,
        req.target_audience,
        req.post_length,
    )

    return GenerateResponse(draft_id=draft.id, session_id=req.session_id)
