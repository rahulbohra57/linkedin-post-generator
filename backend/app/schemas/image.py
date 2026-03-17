from pydantic import BaseModel
from typing import Literal


class ImageResult(BaseModel):
    id: str
    url: str
    thumbnail_url: str
    source: Literal["ai_generated", "stock", "uploaded"]
    prompt: str | None = None
    photographer: str | None = None
    recommended: bool = False
    recommendation_reason: str | None = None


class ImageGenerateRequest(BaseModel):
    draft_id: int
    session_id: str


class ImageListResponse(BaseModel):
    images: list[ImageResult]
    recommended_id: str | None = None
