import secrets
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User
from app.services.linkedin_service import (
    build_auth_url,
    exchange_code_for_token,
    get_linkedin_profile,
)
from app.core.exceptions import LinkedInAuthError
from app.config import get_settings

settings = get_settings()
router = APIRouter()

# In-memory CSRF state store (use Redis in production)
_states: dict[str, str] = {}


@router.get("/auth/linkedin/login")
async def linkedin_login(session_id: str):
    """Redirect user to LinkedIn OAuth consent page."""
    state = secrets.token_urlsafe(16)
    _states[state] = session_id
    return RedirectResponse(url=build_auth_url(state))


@router.get("/auth/linkedin/callback")
async def linkedin_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if error:
        return RedirectResponse(url=f"http://localhost:3000/preview?auth_error={error}")

    if not state or state not in _states:
        raise LinkedInAuthError("Invalid OAuth state. Please try again.")

    session_id = _states.pop(state)

    # Exchange code for tokens
    token_data = await exchange_code_for_token(code)
    profile = await get_linkedin_profile(token_data["access_token"])
    linkedin_urn = f"urn:li:person:{profile['id']}"

    # Upsert user
    result = await db.execute(select(User).where(User.session_id == session_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(session_id=session_id)
        db.add(user)

    user.linkedin_access_token = token_data["access_token"]
    user.linkedin_refresh_token = token_data.get("refresh_token")
    user.linkedin_token_expires_at = token_data["expires_at"]
    user.linkedin_urn = linkedin_urn
    await db.commit()

    return RedirectResponse(url="http://localhost:3000/preview?auth_success=true")


@router.get("/auth/linkedin/status")
async def linkedin_status(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.session_id == session_id))
    user = result.scalar_one_or_none()
    connected = bool(user and user.linkedin_access_token)
    return {"connected": connected, "linkedin_urn": user.linkedin_urn if connected else None}
