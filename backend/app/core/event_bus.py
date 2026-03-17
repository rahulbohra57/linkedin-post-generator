"""
In-memory asyncio-based pub/sub event bus.
Replaces Redis for WebSocket progress streaming — no external dependencies needed.
"""
import asyncio
from collections import defaultdict

# session_id -> list of subscriber queues (one per WebSocket connection)
_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)


async def subscribe(session_id: str) -> asyncio.Queue:
    """Create and register a new queue for the given session."""
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    _queues[session_id].append(q)
    return q


async def unsubscribe(session_id: str, q: asyncio.Queue) -> None:
    """Remove a queue from the session's subscriber list."""
    try:
        _queues[session_id].remove(q)
    except ValueError:
        pass


async def publish(session_id: str, event: dict) -> None:
    """Deliver an event to all subscribers of the given session."""
    for q in list(_queues.get(session_id, [])):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
