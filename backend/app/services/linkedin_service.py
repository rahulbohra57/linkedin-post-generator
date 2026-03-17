"""
LinkedIn API v2 client.
Handles: OAuth 2.0 token exchange, image upload, ugcPosts creation.
"""
import httpx
from datetime import datetime, timedelta
from app.config import get_settings
from app.core.exceptions import LinkedInAuthError, LinkedInPublishError

settings = get_settings()

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def build_auth_url(state: str) -> str:
    params = (
        f"response_type=code"
        f"&client_id={settings.linkedin_client_id}"
        f"&redirect_uri={settings.linkedin_redirect_uri}"
        f"&scope=w_member_social%20r_liteprofile%20r_emailaddress"
        f"&state={state}"
    )
    return f"{LINKEDIN_AUTH_URL}?{params}"


async def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for access token. Returns token data dict."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.linkedin_redirect_uri,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15.0,
        )
        if response.status_code != 200:
            raise LinkedInAuthError(f"Token exchange failed: {response.text}")
        data = response.json()

    expires_at = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 5184000))
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expires_at": expires_at,
    }


async def get_linkedin_profile(access_token: str) -> dict:
    """Fetch the user's LinkedIn profile to get their URN."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{LINKEDIN_API_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        if response.status_code != 200:
            raise LinkedInAuthError("Failed to fetch LinkedIn profile.")
        return response.json()


async def upload_image_to_linkedin(access_token: str, linkedin_urn: str, image_bytes: bytes) -> str:
    """
    Upload an image to LinkedIn assets.
    Returns the asset URN for use in the post.
    """
    async with httpx.AsyncClient() as client:
        # Step 1: Register upload
        register_response = await client.post(
            f"{LINKEDIN_API_BASE}/assets?action=registerUpload",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json={
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": linkedin_urn,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent",
                        }
                    ],
                }
            },
            timeout=15.0,
        )
        if register_response.status_code != 200:
            raise LinkedInPublishError(f"Image registration failed: {register_response.text}")

        register_data = register_response.json()
        upload_url = (
            register_data["value"]["uploadMechanism"]
            ["com.linkedin.digitalmedia.mediaartifact.ARUpdateUploadRequest"]
            ["uploadUrl"]
        )
        asset_urn = register_data["value"]["asset"]

        # Step 2: Upload binary
        upload_response = await client.put(
            upload_url,
            content=image_bytes,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
        if upload_response.status_code not in (200, 201):
            raise LinkedInPublishError(f"Image upload failed: {upload_response.status_code}")

    return asset_urn


async def create_linkedin_post(
    access_token: str,
    linkedin_urn: str,
    post_text: str,
    asset_urn: str | None = None,
) -> dict:
    """
    Create a LinkedIn ugcPost with optional image.
    Returns the post ID and URL.
    """
    media_category = "IMAGE" if asset_urn else "NONE"
    share_content: dict = {
        "shareCommentary": {"text": post_text},
        "shareMediaCategory": media_category,
    }

    if asset_urn:
        share_content["media"] = [
            {
                "status": "READY",
                "description": {"text": "Post image"},
                "media": asset_urn,
            }
        ]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LINKEDIN_API_BASE}/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json={
                "author": linkedin_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": share_content
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                },
            },
            timeout=20.0,
        )
        if response.status_code not in (200, 201):
            raise LinkedInPublishError(f"Post creation failed: {response.text}")

        post_id = response.headers.get("x-restli-id", "")
        post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else None

    return {"post_id": post_id, "post_url": post_url}
