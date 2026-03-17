import httpx
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PEXELS_BASE_URL = "https://api.pexels.com/v1"


async def search_pexels_images(query: str, count: int = 3) -> list[dict]:
    """
    Search Pexels for stock images related to the query.
    Returns list of {id, url, thumbnail_url, source, photographer}.
    Returns [] on any error so callers can handle gracefully.
    """
    if not settings.pexels_api_key:
        logger.warning("PEXELS_API_KEY not configured — skipping Pexels search")
        return []

    headers = {"Authorization": settings.pexels_api_key}
    params = {
        "query": query,
        "per_page": count,
        # No orientation filter — gives many more results
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PEXELS_BASE_URL}/search",
                headers=headers,
                params=params,
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Pexels API HTTP error for query=%r: %s", query, e)
        return []
    except Exception as e:
        logger.error("Pexels API request failed for query=%r: %s", query, e)
        return []

    images = []
    for photo in data.get("photos", []):
        images.append({
            "id": f"pexels_{photo['id']}",
            "url": photo["src"]["large"],
            "thumbnail_url": photo["src"]["medium"],
            "source": "stock",
            "photographer": photo.get("photographer", ""),
            "prompt": None,
        })

    return images
