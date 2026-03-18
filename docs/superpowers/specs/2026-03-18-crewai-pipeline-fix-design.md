# CrewAI Pipeline Fix — Design Spec
**Date:** 2026-03-18
**Status:** Approved
**Scope:** Fix local and Render.com generation failures (Option A — targeted fixes)

---

## Problem

The LinkedIn post generator stops before CrewAI ever runs. No agent output appears in Docker
logs. The UI shows a waiting state that never resolves. The same failure occurs on Render.com.

### Confirmed Root Causes

1. **`--reload` kills background tasks.** `docker-compose.yml` runs uvicorn with `--reload`
   and mounts `./backend:/app` as a live volume. When uvicorn detects any file change in
   `/app` (e.g. `__pycache__/`, `.pyc` files written at import time), it restarts the child
   process — killing the in-flight `_run_and_save` background task before `crew.kickoff()`
   is reached.

2. **Errors are invisible.** `_run_and_save` catches exceptions, sets `draft.status = "error"`,
   then does `raise exc`. In a FastAPI background task, re-raised exceptions go to the default
   Python logger at WARNING level, which is not shown in Docker's default output. The developer
   sees nothing.

3. **`asyncio.get_event_loop()` is deprecated.** `crew.py` calls
   `asyncio.get_event_loop()` inside a running coroutine. Python 3.10+ deprecated this in
   favour of `asyncio.get_running_loop()`. Inside uvicorn's reload child process this can
   return a closed or wrong loop, causing `run_in_executor` to silently fail.

4. **Unpinned `crewai>=0.70.0`.** crewai 1.x (released 2025) removed `Task.callback` and
   changed `Crew` and `Process` APIs. The Docker layer cache may have resolved to a 1.x
   version, breaking the pipeline without any obvious error.

---

## Solution — Targeted Fixes (Option A)

Five file changes, no structural refactor.

### 1. `docker-compose.yml` — remove `--reload`

**Before:**
```
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
**After:**
```
command: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Rationale: `--reload` is a convenience for code hot-reloading during development, but it
actively monitors the mounted `/app` directory and restarts the server process on any file
change. This kills in-flight background tasks. Since the workflow is already `docker compose
up --build`, code changes trigger a rebuild — `--reload` adds no value and causes the bug.

---

### 2. `backend/app/api/routes/generate.py` — visible error logging

Add `import logging` and a logger instance. Log at the start of `_run_and_save` so the
background task is visibly confirmed in Docker output. Replace the silent `raise exc` with
`logging.exception(...)` before re-raising, so the full stack trace appears in Docker logs.

```python
import logging
logger = logging.getLogger(__name__)

async def _run_and_save(...):
    logger.info("Background task started: draft_id=%s session_id=%s", draft_id, session_id[:8])
    try:
        result = await run_pipeline(...)
        ...
    except Exception as exc:
        logger.exception("Pipeline failed for draft_id=%s: %s", draft_id, exc)
        async with AsyncSessionLocal() as db:
            ...
            draft.status = "error"
            await db.commit()
        raise
```

---

### 3. `backend/app/agents/crew.py` — fix event loop call

**Before:**
```python
loop = asyncio.get_event_loop()
```
**After:**
```python
loop = asyncio.get_running_loop()
```

`get_running_loop()` is guaranteed to return the currently-executing event loop from inside
a coroutine. `get_event_loop()` is deprecated in Python 3.10+ and can return a stale or
closed loop in the uvicorn reload child process context.

---

### 4. `backend/requirements.txt` — pin crewai

Pin `crewai` and `crewai-tools` to the last stable 0.x release that uses the API present
in this codebase (`Task.callback`, `Process.sequential`, `Crew(agents=..., tasks=...)`).
The exact version to pin is determined during implementation by checking the Docker layer
cache (`pip show crewai`) and the crewai changelog.

Target pin range: `crewai>=0.80.0,<1.0.0` and `crewai-tools>=0.14.0,<1.0.0`

---

### 5. `backend/app/agents/crew.py` — log exceptions in run_pipeline

Add `logging.exception` before re-raising in `run_pipeline` so that any LLM or agent
failure is immediately visible in Docker output rather than disappearing into the
background task handler.

```python
except Exception as exc:
    logger.exception("run_pipeline failed for session %s: %s", session_id[:8], exc)
    await publish_event(session_id, make_error_event(str(exc)))
    raise
```

---

## Files Changed

| File | Change |
|------|--------|
| `docker-compose.yml` | Remove `--reload` from backend command |
| `backend/app/api/routes/generate.py` | Add logging, replace silent raise |
| `backend/app/agents/crew.py` | Fix `get_event_loop` → `get_running_loop`, add exception logging |
| `backend/requirements.txt` | Pin crewai and crewai-tools to `<1.0.0` |

---

## Success Criteria

- `docker compose up --build` starts the backend cleanly
- Submitting a generate request produces visible log output confirming the background task
  started, then CrewAI agent output (`verbose=True`) flowing in the terminal
- On success: `draft.status` changes to `"ready"` and `post_text` is populated in the DB
- On failure: full stack trace appears in Docker logs immediately

---

## Out of Scope

- Render.com deployment changes (fix locally first; same code ships to Render via Docker)
- WebSocket / frontend changes
- LLM provider changes (Gemini/HuggingFace selection left as-is)
- Redis — not used by the event bus; no changes needed
