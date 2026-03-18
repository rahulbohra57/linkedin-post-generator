# CrewAI Pipeline Fix — Design Spec
**Date:** 2026-03-18
**Status:** Approved
**Scope:** Fix local Docker generation failures (Option A — targeted fixes)

---

## Problem

The LinkedIn post generator stops before CrewAI ever runs. No agent output appears in Docker
logs. The UI shows a waiting state that never resolves.

### Confirmed Root Causes

1. **`--reload` kills background tasks (local Docker only).**
   `docker-compose.yml` runs uvicorn with `--reload` and mounts `./backend:/app` as a live
   volume. When uvicorn detects any file change in `/app` (e.g. `__pycache__/`, `.pyc` files
   written at import time), it restarts the child process — killing the in-flight
   `_run_and_save` background task before `crew.kickoff()` is reached.
   Note: the `backend/Dockerfile` `CMD` does NOT include `--reload`; this bug is
   compose-only and does not affect Render.com deployments (which run the image directly).

2. **Background task errors are completely invisible.**
   `generate.py` has no `import logging` and no logger instance. `_run_and_save` catches
   all exceptions, sets `draft.status = "error"`, then does `raise exc` with zero logging
   output. There is no call to `logger.exception`, `print`, or any output function. The
   exception disappears entirely — the developer sees nothing in Docker logs.

3. **`_emit` callback failures are silently dropped.**
   `crew.py:_emit()` calls `asyncio.run_coroutine_threadsafe(publish_event(...), loop)`
   as fire-and-forget (no `.result()` call, no try/except). If `publish_event` raises or
   the queue is full, the error is silently discarded. This hides event-bus failures during
   the pipeline run.

4. **`asyncio.get_event_loop()` is deprecated.**
   `crew.py` calls `asyncio.get_event_loop()` inside a running coroutine. Python 3.10+
   deprecated this in favour of `asyncio.get_running_loop()`. In the uvicorn `--reload`
   child process, this can return a stale loop causing `run_in_executor` to fail silently.
   In non-reload contexts (including Render.com) this is a DeprecationWarning rather than
   a crash — but `get_running_loop()` is the correct API regardless.

5. **Unpinned `crewai>=0.70.0`.**
   crewai 1.x (released 2025) removed `Task.callback` and changed `Crew` and `Process`
   APIs. The Docker layer cache may have resolved to a 1.x version, breaking the pipeline.
   `crewai-tools`, `langchain-community`, and `langchain-tavily` are similarly unpinned
   and have inter-version compatibility requirements with crewai. All must be pinned
   in lockstep after verifying which versions were working together.

---

## Solution — Targeted Fixes (Option A)

Six file changes, no structural refactor.

### 1. `docker-compose.yml` — remove `--reload`

**Before:**
```
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
**After:**
```
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
```

Adding `--log-level info` ensures uvicorn propagates INFO-level output including the
`crewai` logger namespace used by `verbose=True` agents.

---

### 2. `backend/app/api/routes/generate.py` — add logging

Add `import logging` and a module-level `logger`. Add an INFO log at the start of
`_run_and_save` confirming the background task is running. Replace the silent `raise exc`
with `logger.exception(...)` before re-raising.

```python
import logging
logger = logging.getLogger(__name__)

async def _run_and_save(...):
    logger.info("Background task started: draft_id=%s session_id=%.8s", draft_id, session_id)
    try:
        result = await run_pipeline(...)
        ...
    except Exception as exc:
        logger.exception("Pipeline failed for draft_id=%s", draft_id)
        async with AsyncSessionLocal() as db:
            ...
            draft.status = "error"
            await db.commit()
        raise
```

---

### 3. `backend/app/agents/crew.py` — fix event loop + log `_emit` errors

**Fix A — event loop:**
```python
# Before
loop = asyncio.get_event_loop()
# After
loop = asyncio.get_running_loop()
```

**Fix B — log `_emit` failures:**
Wrap the `run_coroutine_threadsafe` call in `_emit` with try/except for synchronous
scheduling errors, and attach a `done_callback` to observe asynchronous failures inside
`publish_event` (the common case — scheduling errors are rare):

```python
def _emit(loop, session_id, agent_name, output):
    def _on_done(fut):
        exc = fut.exception()
        if exc:
            logger.warning("_emit failed for agent=%s session=%.8s: %s", agent_name, session_id, exc)
    try:
        fut = asyncio.run_coroutine_threadsafe(
            publish_event(session_id, make_agent_complete_event(agent_name, output)),
            loop,
        )
        fut.add_done_callback(_on_done)
    except Exception as e:
        logger.warning("_emit scheduling failed for agent=%s session=%.8s: %s", agent_name, session_id, e)
```

**Fix C — log `run_pipeline` exceptions:**
```python
except Exception as exc:
    logger.exception("run_pipeline failed for session=%.8s", session_id)
    await publish_event(session_id, make_error_event(str(exc)))
    raise
```

---

### 4. `backend/requirements.txt` — pin crewai ecosystem

During implementation: run `docker compose run backend pip show crewai crewai-tools
langchain-community langchain-tavily` to identify currently installed versions. Pin all
four packages to those exact versions using `==` to prevent future upgrades from breaking
the API again. If the currently installed crewai is ≥1.0, install the latest 0.x release
instead and verify `Task.callback` and `Process.sequential` work.

Target constraint: `crewai>=0.80.0,<1.0.0` with crewai-tools, langchain-community, and
langchain-tavily pinned to compatible versions verified against the crewai changelog.

---

## Files Changed

| File | Change |
|------|--------|
| `docker-compose.yml` | Remove `--reload`, add `--log-level info` |
| `backend/app/api/routes/generate.py` | Add logging, replace silent raise |
| `backend/app/agents/crew.py` | Fix `get_event_loop` → `get_running_loop`, log `_emit` failures, log pipeline exceptions |
| `backend/requirements.txt` | Pin crewai, crewai-tools, langchain-community, langchain-tavily |

---

## Success Criteria

- `docker compose up --build` starts the backend cleanly with no import errors
- Submitting a generate request produces a visible log line: `"Background task started: draft_id=..."`
- CrewAI agent output (`Researcher`, `Tone Analyzer`, etc.) flows in the terminal as each
  agent completes (confirmed by `verbose=True` + `--log-level info` propagating the `crewai`
  logger namespace)
- On success: `draft.status` changes to `"ready"` and `post_text` is non-empty in the DB
- On any failure: full stack trace appears immediately in Docker logs via `logger.exception`

---

## Out of Scope

- Render.com deployment changes (same Docker image ships automatically; `--reload` was never
  used there, so root cause 1 does not apply to Render)
- WebSocket / frontend changes
- LLM provider changes (Gemini/HuggingFace selection left as-is)
- Redis — not used by the event bus; no changes needed
