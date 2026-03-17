import uuid
import io
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import InferenceClient
from app.config import get_settings

settings = get_settings()

# Thread pool for running sync HF calls in async context
_executor = ThreadPoolExecutor(max_workers=3)


def _generate_hf_image_sync(prompt: str) -> bytes:
    """
    Generate an image with FLUX.1-schnell (free HuggingFace Inference API).
    Returns raw PNG bytes.
    """
    client = InferenceClient(token=settings.huggingfacehub_api_token)
    pil_image = client.text_to_image(
        prompt,
        model="black-forest-labs/FLUX.1-schnell",
    )
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()


async def generate_image_hf(prompt: str) -> dict:
    """
    Generate a single image with FLUX.1-schnell and save it locally.
    Returns: {id, url, thumbnail_url, prompt, source}
    """
    loop = asyncio.get_event_loop()
    image_bytes = await loop.run_in_executor(_executor, _generate_hf_image_sync, prompt)

    image_id = str(uuid.uuid4())
    storage_path = Path(settings.local_storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    local_path = storage_path / f"{image_id}.png"
    local_path.write_bytes(image_bytes)

    return {
        "id": image_id,
        "url": f"/storage/{image_id}.png",
        "thumbnail_url": f"/storage/{image_id}.png",
        "source": "ai_generated",
        "prompt": prompt,
    }


async def generate_images_batch(prompts: list[str]) -> list[dict]:
    """Generate multiple images concurrently via HuggingFace FLUX.1-schnell."""
    tasks = [generate_image_hf(p) for p in prompts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, dict)]
