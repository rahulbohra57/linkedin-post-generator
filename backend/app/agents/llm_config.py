"""
LLM routing configuration.

Set PRIMARY_LLM in your .env to choose the model for creative/reasoning tasks:
  PRIMARY_LLM=gemma       → gemma-3-27b-it via Google AI (uses GEMINI_API_KEY, free)
  PRIMARY_LLM=gemini      → gemini-2.0-flash via Google AI (uses GEMINI_API_KEY)
  PRIMARY_LLM=claude      → claude-sonnet-4-6 (uses ANTHROPIC_API_KEY)
  PRIMARY_LLM=huggingface → Qwen2.5-7B via HuggingFace router (uses HF token)
"""
import os
from crewai import LLM
from app.config import get_settings

settings = get_settings()

# Which model to use for creative tasks. Defaults to gemma (free, no quota issues).
_PRIMARY = os.environ.get("PRIMARY_LLM", "gemma").lower()

# LiteLLM uses HUGGINGFACE_API_KEY; map from our token name
_HF_TOKEN = settings.huggingfacehub_api_token
if _HF_TOKEN:
    os.environ.setdefault("HUGGINGFACE_API_KEY", _HF_TOKEN)


def get_gemma_primary() -> LLM:
    """
    Gemma 3 4B via Google AI Studio (free, 30 RPM — sufficient for the full pipeline).
    Using 4B instead of 27B to avoid the 2 RPM rate limit on larger models.
    """
    return LLM(
        model="gemini/gemma-3-4b-it",
        api_key=settings.gemini_api_key,
        temperature=0.7,
        max_tokens=4096,
    )


def get_gemma_fast() -> LLM:
    """Gemma 3 4B — fast, free, good for formatting/classification tasks."""
    return LLM(
        model="gemini/gemma-3-4b-it",
        api_key=settings.gemini_api_key,
        temperature=0.3,
        max_tokens=2048,
    )


def get_huggingface_primary() -> LLM:
    """Qwen2.5-7B via HuggingFace OpenAI-compatible router."""
    return LLM(
        model="openai/Qwen/Qwen2.5-7B-Instruct",
        api_base="https://router.huggingface.co/v1",
        api_key=_HF_TOKEN,
        temperature=0.7,
        max_tokens=2048,
    )


def get_huggingface_fast() -> LLM:
    """Qwen2.5-7B via HuggingFace router (fast classification tasks)."""
    return LLM(
        model="openai/Qwen/Qwen2.5-7B-Instruct",
        api_base="https://router.huggingface.co/v1",
        api_key=_HF_TOKEN,
        temperature=0.3,
        max_tokens=1024,
    )


def get_claude() -> LLM:
    return LLM(
        model="claude-sonnet-4-6",
        api_key=settings.anthropic_api_key,
        temperature=0.7,
        max_tokens=4096,
    )


def get_claude_fast() -> LLM:
    """Claude Haiku — cheap and fast, for tone analysis, hashtags, assembly."""
    return LLM(
        model="claude-haiku-4-5",
        api_key=settings.anthropic_api_key,
        temperature=0.3,
        max_tokens=2048,
    )


def get_gemini_pro() -> LLM:
    return LLM(
        model="gemini/gemini-2.0-flash",
        api_key=settings.gemini_api_key,
        temperature=0.7,
        max_tokens=4096,
    )


def get_gemini_fast() -> LLM:
    return LLM(
        model="gemini/gemini-2.0-flash",
        api_key=settings.gemini_api_key,
        temperature=0.3,
        max_tokens=2048,
    )


# Cached instances
_primary_llm: LLM | None = None
_fast_llm: LLM | None = None


def primary() -> LLM:
    """
    Primary LLM for writing, editing, image prompts, and research synthesis.
    Controlled by PRIMARY_LLM env var (default: gemma — free, no daily quota issues).
    """
    global _primary_llm
    if _primary_llm is None:
        if _PRIMARY == "claude" and settings.anthropic_api_key:
            _primary_llm = get_claude()
        elif _PRIMARY == "gemini" and settings.gemini_api_key:
            _primary_llm = get_gemini_pro()
        elif _PRIMARY == "gemma" and settings.gemini_api_key:
            _primary_llm = get_gemma_primary()
        elif _PRIMARY == "huggingface" and _HF_TOKEN:
            _primary_llm = get_huggingface_primary()
        elif settings.gemini_api_key:
            # Auto-fallback: try Gemma (free tier, no daily limit issues)
            _primary_llm = get_gemma_primary()
        else:
            _primary_llm = get_huggingface_primary()
    return _primary_llm


def fast() -> LLM:
    """Fast LLM for tone analysis, hashtag ranking, post assembly."""
    global _fast_llm
    if _fast_llm is None:
        if _PRIMARY == "claude" and settings.anthropic_api_key:
            _fast_llm = get_claude_fast()
        elif _PRIMARY in ("gemini", "gemma") and settings.gemini_api_key:
            _fast_llm = get_gemma_fast()
        elif settings.gemini_api_key:
            _fast_llm = get_gemma_fast()
        else:
            _fast_llm = get_huggingface_fast()
    return _fast_llm


# Keep old names as aliases so nothing else breaks
def claude() -> LLM:
    return primary()


def gemini() -> LLM:
    return fast()
