import asyncio
from app.core.event_bus import publish as bus_publish


async def publish_event(session_id: str, event: dict) -> None:
    """Publish a progress event to the in-memory event bus."""
    try:
        await bus_publish(session_id, event)
    except Exception:
        pass


def make_agent_start_event(agent_name: str) -> dict:
    return {"event": "agent_start", "agent": agent_name}


def make_agent_complete_event(agent_name: str, output: str) -> dict:
    return {"event": "agent_complete", "agent": agent_name, "output": output[:300]}


def make_pipeline_done_event(post_text: str, quality_score: float, hashtags: str) -> dict:
    return {
        "event": "pipeline_done",
        "post_text": post_text,
        "quality_score": quality_score,
        "hashtags": hashtags,
    }


def make_error_event(message: str) -> dict:
    return {"event": "error", "message": message}
