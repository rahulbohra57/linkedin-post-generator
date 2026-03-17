from pydantic import BaseModel
from datetime import datetime


class PublishRequest(BaseModel):
    draft_id: int
    session_id: str
    image_url: str | None = None


class PublishResult(BaseModel):
    success: bool
    linkedin_post_url: str | None = None
    linkedin_post_id: str | None = None
    published_at: datetime | None = None
    error: str | None = None
