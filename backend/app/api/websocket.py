"""
WebSocket endpoint: streams CrewAI pipeline progress events to the client.

Flow:
  1. Client connects to ws://backend/ws/progress/{session_id}
  2. Backend subscribes to the in-memory event bus for this session
  3. As agents complete, crew.py publishes events to the bus
  4. This handler forwards each event as a JSON string to the WebSocket
  5. Connection closes after pipeline_done or error event (or 5-min timeout)
"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.event_bus import subscribe, unsubscribe

router = APIRouter()


@router.websocket("/ws/progress/{session_id}")
async def progress_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    q = await subscribe(session_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=300.0)
            except asyncio.TimeoutError:
                break

            data = json.dumps(event)
            await websocket.send_text(data)

            if event.get("event") in ("pipeline_done", "error"):
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"event": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        await unsubscribe(session_id, q)
        try:
            await websocket.close()
        except Exception:
            pass
