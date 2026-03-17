from pydantic import BaseModel
from datetime import datetime


class DraftUpdate(BaseModel):
    post_text: str | None = None
    selected_image_url: str | None = None


class DraftOut(BaseModel):
    id: int
    topic: str
    tone: str
    target_audience: str | None
    post_text: str | None
    hashtags: str | None
    quality_score: float | None
    quality_notes: str | None
    character_count: int | None
    selected_image_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
