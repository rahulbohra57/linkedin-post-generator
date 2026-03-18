# CrewAI Pipeline Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the LinkedIn post generator so CrewAI agents run to completion locally and on Render.com.

**Architecture:** Four targeted fixes — remove `--reload` from docker-compose to stop uvicorn killing background tasks, add structured logging so failures are visible, fix the Python 3.10+ event loop API call, and pin the crewai package ecosystem to the verified-working installed versions to prevent future breakage.

**Tech Stack:** FastAPI background tasks, CrewAI 0.193.2, asyncio thread pool executor, Docker Compose, uvicorn

**Spec:** `docs/superpowers/specs/2026-03-18-crewai-pipeline-fix-design.md`

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `docker-compose.yml` | Modify | Remove `--reload`, add `--log-level info` to backend command |
| `backend/app/api/routes/generate.py` | Modify | Add `import logging`, module logger, log task start, replace silent raise |
| `backend/app/agents/crew.py` | Modify | `get_event_loop` → `get_running_loop`, fix `_emit` with done_callback, log pipeline exceptions |
| `backend/requirements.txt` | Modify | Pin crewai==0.193.2, crewai-tools==0.71.0, langchain-community==0.3.27, langchain-tavily==0.2.17 |

---

## Task 1: Remove `--reload` from docker-compose.yml

**File:** `docker-compose.yml:33`

**Why:** uvicorn `--reload` with `./backend:/app` volume mount watches the entire source tree for changes. The host's `__pycache__/*.pyc` files are inside the mounted volume. When uvicorn detects them on startup it restarts the child process, killing the in-flight `_run_and_save` background task before `crew.kickoff()` is ever reached.

- [ ] **Step 1: Edit docker-compose.yml**

Open `docker-compose.yml`. Find line 33:
```yaml
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Change it to:
```yaml
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
```
`--log-level info` ensures the `crewai` logger namespace (used by `verbose=True` agents) propagates to Docker output.

- [ ] **Step 2: Verify the change**

```bash
grep "command:" docker-compose.yml
```
Expected output:
```
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
    command: npm run start
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "fix: remove uvicorn --reload to stop background task killing"
```

---

## Task 2: Add structured logging to generate.py

**File:** `backend/app/api/routes/generate.py`

**Why:** The `_run_and_save` background task has no `import logging` and no logger. When it catches an exception and re-raises, there is zero output anywhere — the developer sees nothing. Adding logging makes every failure immediately visible in Docker logs.

- [ ] **Step 1: Read the current file**

Read `backend/app/api/routes/generate.py` and note the top imports and `_run_and_save` function (lines 1-49).

- [ ] **Step 2: Add logging import and logger**

At the top of the file, after the existing imports, add:
```python
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 3: Add task-start log and replace silent raise in `_run_and_save`**

The current `_run_and_save` function looks like:
```python
async def _run_and_save(
    draft_id: int,
    session_id: str,
    topic: str,
    tone: str,
    target_audience: str,
    post_length: str,
):
    """Background task: run pipeline, then update the draft in DB."""
    from app.db.database import AsyncSessionLocal

    try:
        result = await run_pipeline(session_id, topic, tone, target_audience, post_length)
        ...
    except Exception as exc:
        async with AsyncSessionLocal() as db:
            draft = await db.get(Draft, draft_id)
            if draft:
                draft.status = "error"
                await db.commit()
        raise exc
```

Change it so it logs at task start and uses `logger.exception` on failure:
```python
async def _run_and_save(
    draft_id: int,
    session_id: str,
    topic: str,
    tone: str,
    target_audience: str,
    post_length: str,
):
    """Background task: run pipeline, then update the draft in DB."""
    from app.db.database import AsyncSessionLocal

    logger.info("Background task started: draft_id=%s session_id=%.8s", draft_id, session_id)
    try:
        result = await run_pipeline(session_id, topic, tone, target_audience, post_length)

        # Persist image prompts to session for image endpoint
        await set_session_data(session_id, "image_prompts", result.get("image_prompts", []))

        async with AsyncSessionLocal() as db:
            draft = await db.get(Draft, draft_id)
            if draft:
                draft.post_text = result["post_text"]
                draft.hashtags = result["hashtags"]
                draft.quality_score = result["quality_score"]
                draft.quality_notes = "\n".join(result.get("quality_notes", []))
                draft.character_count = result["character_count"]
                draft.pexels_queries = json.dumps(result.get("image_prompts", []))
                draft.status = "ready"
                await db.commit()
    except Exception as exc:
        logger.exception("Pipeline failed for draft_id=%s", draft_id)
        async with AsyncSessionLocal() as db:
            draft = await db.get(Draft, draft_id)
            if draft:
                draft.status = "error"
                await db.commit()
        raise
```

Note: `raise exc` → bare `raise` (re-raises with original traceback intact).

- [ ] **Step 4: Remove the now-unused `import asyncio`**

The original `generate.py` has `import asyncio` at line 1. After this task's changes, `asyncio`
is never referenced directly in this file (async functions do not require it). Remove that line.

- [ ] **Step 5: Verify the file looks correct**

Read the modified `backend/app/api/routes/generate.py` and confirm:
- `import asyncio` is **not** present
- `import logging` is present
- `logger = logging.getLogger(__name__)` is present
- `_run_and_save` starts with `logger.info("Background task started: ...")`
- The except block has `logger.exception(...)` before `raise`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/generate.py
git commit -m "fix: add logging to background task so pipeline failures are visible"
```

---

## Task 3: Fix crew.py — event loop, _emit callback, pipeline logging

**File:** `backend/app/agents/crew.py`

**Why:** Three issues in this file:
1. `asyncio.get_event_loop()` is deprecated in Python 3.10+ — use `get_running_loop()` which is guaranteed to return the active loop from a coroutine context.
2. `_emit()` uses fire-and-forget `run_coroutine_threadsafe()` with no error handling — if `publish_event` fails asynchronously, the error disappears. Add a `done_callback` to observe Future failures.
3. `run_pipeline` catches exceptions and re-raises with no logging — add `logger.exception` so any LLM or agent failure appears in Docker logs.

- [ ] **Step 1: Read the current file**

Read `backend/app/agents/crew.py` — focus on:
- Line ~69: `loop = asyncio.get_event_loop()`
- Lines ~346-351: `_emit()` function
- Lines ~90-92: except block in `run_pipeline`

- [ ] **Step 2: Add logging import and logger at top of file**

After the existing imports at the top of the file, add:
```python
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 3: Fix `asyncio.get_event_loop()` → `asyncio.get_running_loop()`**

In `run_pipeline`, change:
```python
loop = asyncio.get_event_loop()
```
to:
```python
loop = asyncio.get_running_loop()
```

- [ ] **Step 4: Fix `_emit` to observe async Future failures**

Replace the entire `_emit` function:

**Before:**
```python
def _emit(loop: asyncio.AbstractEventLoop, session_id: str, agent_name: str, output: str):
    """Fire-and-forget event emit from sync context."""
    asyncio.run_coroutine_threadsafe(
        publish_event(session_id, make_agent_complete_event(agent_name, output)),
        loop,
    )
```

**After:**

Note: `asyncio.run_coroutine_threadsafe()` returns a `concurrent.futures.Future`, NOT an
`asyncio.Future`. The done callback must guard against cancellation before calling
`.exception()`, otherwise a cancelled future (e.g. on shutdown) will raise
`concurrent.futures.CancelledError` inside the callback.

```python
import concurrent.futures  # add to existing imports at top of file

def _emit(loop: asyncio.AbstractEventLoop, session_id: str, agent_name: str, output: str):
    """Emit agent_complete event from sync thread context."""
    def _on_done(fut: concurrent.futures.Future) -> None:
        if fut.cancelled():
            return
        exc = fut.exception()
        if exc:
            logger.warning(
                "_emit failed for agent=%s session=%.8s: %s", agent_name, session_id, exc
            )

    try:
        fut = asyncio.run_coroutine_threadsafe(
            publish_event(session_id, make_agent_complete_event(agent_name, output)),
            loop,
        )
        fut.add_done_callback(_on_done)
    except Exception as e:
        logger.warning(
            "_emit scheduling failed for agent=%s session=%.8s: %s", agent_name, session_id, e
        )
```

- [ ] **Step 5: Add `logger.exception` in `run_pipeline` except block**

In `run_pipeline`, the current except block is:
```python
    except Exception as exc:
        await publish_event(session_id, make_error_event(str(exc)))
        raise
```

Change it to:
```python
    except Exception as exc:
        logger.exception("run_pipeline failed for session=%.8s", session_id)
        await publish_event(session_id, make_error_event(str(exc)))
        raise
```

- [ ] **Step 6: Verify the file looks correct**

Read the modified `backend/app/agents/crew.py` and confirm:
- `import logging` and `logger = logging.getLogger(__name__)` are present
- `loop = asyncio.get_running_loop()` (not `get_event_loop`)
- `_emit` function has `_on_done` callback with `fut.add_done_callback(_on_done)`
- `run_pipeline` except block has `logger.exception(...)` before the publish and raise

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/crew.py
git commit -m "fix: use get_running_loop(), log _emit failures and pipeline exceptions"
```

---

## Task 4: Pin crewai ecosystem in requirements.txt

**File:** `backend/requirements.txt`

**Why:** Currently `crewai>=0.70.0` with no upper bound. The installed version is 0.193.2. Leaving this unpinned means a future `pip install` could install crewai 1.x (which has breaking API changes) or a crewai-tools/langchain version incompatible with 0.193.2. Pinning to exact versions prevents silent future breakage.

**Verified installed versions (from `pip show` in the Docker image):**
- `crewai==0.193.2`
- `crewai-tools==0.71.0`
- `langchain-community==0.3.27`
- `langchain-tavily==0.2.17`

- [ ] **Step 1: Update requirements.txt**

In `backend/requirements.txt`, find and replace the crewai block:

**Before:**
```
crewai>=0.70.0
crewai-tools>=0.14.0
langchain-tavily>=0.1.5
langchain-community>=0.3.0
```

**After:**
```
crewai==0.193.2
crewai-tools==0.71.0
langchain-tavily==0.2.17
langchain-community==0.3.27
```

- [ ] **Step 2: Verify the change**

```bash
grep -E "crewai|langchain" backend/requirements.txt
```
Expected output:
```
crewai==0.193.2
crewai-tools==0.71.0
langchain-tavily==0.2.17
langchain-community==0.3.27
```

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "fix: pin crewai ecosystem to verified-working versions"
```

---

## Task 5: End-to-end verification

**Why:** All four fixes are applied — now confirm generation actually works locally.

- [ ] **Step 1: Rebuild and start Docker Compose**

```bash
docker compose down && docker compose up --build
```

Wait for:
```
backend-1  | INFO:     Application startup complete.
```

- [ ] **Step 2: Submit a generate request**

In a second terminal:
```bash
curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI agents in 2026",
    "tone": "professional",
    "target_audience": "software engineers",
    "post_length": "short",
    "session_id": "test-session-001"
  }' | python3 -m json.tool
```

Expected response:
```json
{
    "draft_id": 1,
    "session_id": "test-session-001"
}
```

- [ ] **Step 3: Verify background task started in Docker logs**

In the Docker Compose terminal, within 1-2 seconds of the curl you should see:
```
backend-1  | INFO     app.api.routes.generate:generate.py:XX Background task started: draft_id=1 session_id=test-ses
```

- [ ] **Step 4: Verify CrewAI agents running**

Within 10-30 seconds you should see CrewAI verbose output flowing:
```
backend-1  | # Agent: Senior Research Analyst
backend-1  | ## Task: Research the topic: 'AI agents in 2026'...
```

- [ ] **Step 5: Verify draft reaches "ready" status**

Poll the draft status (replace `1` with the actual draft_id from Step 2):
```bash
watch -n 3 'curl -s "http://localhost:8000/api/drafts/1?session_id=test-session-001" | python3 -m json.tool | grep status'
```

Expected (after 2-5 minutes depending on LLM speed):
```json
    "status": "ready",
```

- [ ] **Step 6: Verify post_text is populated**

```bash
curl -s "http://localhost:8000/api/drafts/1?session_id=test-session-001" | python3 -m json.tool | grep -A 3 "post_text"
```

Expected: `post_text` is a non-empty string (the LinkedIn post).

- [ ] **Step 7: Final commit if any debug changes were made**

If any files were changed during debugging, commit them:
```bash
git add -A
git commit -m "fix: verify CrewAI pipeline end-to-end locally"
```

---

## Troubleshooting

**If background task log line never appears:**
- The endpoint is not returning a draft_id, OR the background task is crashing at import time
- Check `docker compose logs backend` for any `ImportError` or `ModuleNotFoundError`

**If background task starts but no CrewAI output appears:**
- LLM API call is failing (bad key, rate limit, network)
- Check Docker logs for `logger.exception` output from `run_pipeline`
- Verify `.env` has valid keys: `GEMINI_API_KEY`, `TAVILY_API_KEY`, `PEXELS_API_KEY`

**If CrewAI output appears but draft never reaches "ready":**
- One agent is hanging past its `max_execution_time`
- Check logs for which agent stops reporting progress
- The Researcher has a 90s timeout; if Tavily is slow this is the usual suspect

**If uvicorn still restarts:**
- Add `PYTHONDONTWRITEBYTECODE=1` to the `environment:` block in `docker-compose.yml`
- This prevents Python from creating `__pycache__/*.pyc` files in the mounted volume

```yaml
environment:
  - PYTHONDONTWRITEBYTECODE=1
  - REDIS_URL=redis://redis:6379/0
  - DATABASE_URL=sqlite+aiosqlite:///./data/linkedin_posts.db
  - LOCAL_STORAGE_PATH=/app/storage/images
```
