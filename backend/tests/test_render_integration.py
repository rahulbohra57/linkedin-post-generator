"""
Integration tests against the live Render.com deployment.

These tests verify the full stack is working:
  - Backend health endpoint responds
  - Frontend serves HTML
  - Backend CORS is configured correctly
  - Backend /api/generate accepts requests

Run with:
  pytest backend/tests/test_render_integration.py -v

Set BACKEND_URL / FRONTEND_URL env vars to override the defaults.
"""
import os
import time
import pytest
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "https://linkedin-post-generator-api.onrender.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://linkedin-post-generator-jztf.onrender.com")

# Render free tier can take up to 90s to wake up
WAKE_TIMEOUT = int(os.getenv("WAKE_TIMEOUT", "90"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_with_wake(url: str, timeout: int = WAKE_TIMEOUT) -> httpx.Response:
    """
    Poll `url` until it returns a non-5xx response or timeout is reached.
    Simulates the backend cold-start scenario on Render free tier.
    """
    deadline = time.time() + timeout
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            resp = httpx.get(url, timeout=15, follow_redirects=True)
            if resp.status_code < 500:
                return resp
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            last_exc = e
        time.sleep(3)
    if last_exc:
        raise last_exc
    raise TimeoutError(f"Backend did not wake within {timeout}s: {url}")


# ---------------------------------------------------------------------------
# Backend tests
# ---------------------------------------------------------------------------

class TestBackendHealth:
    def test_health_returns_200(self):
        """Backend /health must respond with 200 and status=ok."""
        resp = get_with_wake(f"{BACKEND_URL}/health")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_health_body_has_status_ok(self):
        """Backend /health must return JSON with status=ok."""
        resp = get_with_wake(f"{BACKEND_URL}/health")
        body = resp.json()
        assert body.get("status") == "ok", f"Unexpected body: {body}"


class TestBackendCORS:
    def test_cors_allows_frontend_origin(self):
        """
        Backend must send Access-Control-Allow-Origin for the frontend origin.
        This is critical — if CORS is misconfigured the frontend JS can't call the API.
        """
        resp = httpx.options(
            f"{BACKEND_URL}/health",
            headers={
                "Origin": FRONTEND_URL,
                "Access-Control-Request-Method": "GET",
            },
            timeout=15,
            follow_redirects=True,
        )
        # Either 200 or 204 is acceptable for OPTIONS preflight
        assert resp.status_code in (200, 204), f"CORS preflight failed: {resp.status_code}"
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao in (FRONTEND_URL, "*"), (
            f"Expected Access-Control-Allow-Origin={FRONTEND_URL!r}, got {acao!r}"
        )


class TestBackendGenerateEndpoint:
    def test_generate_accepts_valid_request(self):
        """
        POST /api/generate must accept a well-formed request and return a draft_id.
        The pipeline runs in the background — this just verifies the API layer works.
        """
        # Make sure backend is awake first
        get_with_wake(f"{BACKEND_URL}/health")

        payload = {
            "topic": "Integration test post — please ignore",
            "tone": "professional",
            "target_audience": "Developers",
            "post_length": "short",
            "session_id": "pytest-integration-test-session",
        }
        resp = httpx.post(
            f"{BACKEND_URL}/api/generate",
            json=payload,
            timeout=30,
            follow_redirects=True,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        body = resp.json()
        assert "draft_id" in body, f"Missing draft_id in response: {body}"
        assert isinstance(body["draft_id"], int), f"draft_id should be int: {body['draft_id']}"

    def test_generate_rejects_missing_topic(self):
        """POST /api/generate must return 422 when topic is missing."""
        get_with_wake(f"{BACKEND_URL}/health")
        resp = httpx.post(
            f"{BACKEND_URL}/api/generate",
            json={"tone": "professional", "post_length": "short", "session_id": "test"},
            timeout=15,
            follow_redirects=True,
        )
        assert resp.status_code == 422, f"Expected 422 for missing topic, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Frontend tests
# ---------------------------------------------------------------------------

class TestFrontend:
    def test_homepage_returns_200(self):
        """Frontend home page must return 200 with HTML."""
        resp = httpx.get(FRONTEND_URL, timeout=30, follow_redirects=True)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_homepage_is_html(self):
        """Frontend home page must return HTML content."""
        resp = httpx.get(FRONTEND_URL, timeout=30, follow_redirects=True)
        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type, f"Expected HTML, got {content_type}"

    def test_homepage_contains_linkedin_heading(self):
        """Frontend home page must contain the app title."""
        resp = httpx.get(FRONTEND_URL, timeout=30, follow_redirects=True)
        assert "LinkedIn" in resp.text, "App title not found in HTML"

    def test_health_proxy_wakes_backend(self):
        """
        Frontend /api/health-proxy must eventually return 200 by waking the backend.
        This is the keep-alive mechanism used by the homepage before submission.
        """
        resp = httpx.get(
            f"{FRONTEND_URL}/api/health-proxy",
            timeout=90,  # health-proxy waits up to 60s for backend
            follow_redirects=True,
        )
        assert resp.status_code == 200, (
            f"health-proxy returned {resp.status_code}: {resp.text[:200]}"
        )
        body = resp.json()
        assert body.get("status") == "ok", f"Expected status=ok from health-proxy: {body}"
