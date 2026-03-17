from pydantic import BaseModel, Field
from typing import Literal


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=512, description="LinkedIn post topic")
    tone: Literal["professional", "conversational", "thought_leader", "educational", "inspirational"] = "professional"
    target_audience: str = Field(default="professionals", max_length=256)
    post_length: Literal["short", "medium", "long"] = "medium"
    session_id: str = Field(..., description="Client session ID for WebSocket progress tracking")


class GenerateResponse(BaseModel):
    draft_id: int
    session_id: str
    status: str = "generating"
    message: str = "Post generation started. Connect to WebSocket for live progress."
