"""
In-memory session state. Stores transient data (image prompts, pipeline results)
that don't need to persist long-term in the DB.
"""
import json
from typing import Any

# Simple in-memory store: {session_id: {key: value}}
_store: dict[str, dict[str, str]] = {}


async def set_session_data(session_id: str, key: str, value: Any, ttl: int = 3600) -> None:
    if session_id not in _store:
        _store[session_id] = {}
    _store[session_id][key] = json.dumps(value)


async def get_session_data(session_id: str, key: str) -> Any:
    try:
        raw = _store.get(session_id, {}).get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None
