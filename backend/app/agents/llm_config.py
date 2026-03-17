"""
LLM routing configuration.

Set PRIMARY_LLM in your .env to choose the model for creative/reasoning tasks:
  PRIMARY_LLM=huggingface  → mistralai/Mistral-7B-Instruct-v0.3 (default, FREE)
  PRIMARY_LLM=gemini       → gemini/gemini-2.5-flash (uses GEMINI_API_KEY)
  PRIMARY_LLM=claude       → claude-sonnet-4-6 (uses ANTHROPIC_API_KEY)

All free tier: set PRIMARY_LLM=huggingface — only HUGGINGFACEHUB_API_TOKEN needed.
Fast LLM uses zephyr-7b-beta (free HuggingFace) for tone analysis, hashtags, assembly.
"""
import os
from crewai import LLM
from app.config import get_settings

settings = get_settings()

# Which model to use for creative tasks. Defaults to huggingface (fully free).
_PRIMARY = os.environ.get("PRIMARY_LLM", "huggingface").lower()

# LiteLLM uses HUGGINGFACE_API_KEY; map from our token name
_HF_TOKEN = settings.huggingfacehub_api_token
if _HF_TOKEN:
    os.environ.setdefault("HUGGINGFACE_API_KEY", _HF_TOKEN)


def get_huggingface_primary() -> LLM:
    """
    Qwen2.5-7B via HuggingFace OpenAI-compatible API (free).
    Uses /v1 endpoint which supports chat completions natively.
    """
    return LLM(
        model="openai/Qwen/Qwen2.5-7B-Instruct",
        api_base="https://router.huggingface.co/v1",
        api_key=_HF_TOKEN,
        temperature=0.7,
        max_tokens=2048,
    )


def get_huggingface_fast() -> LLM:
    """
    Qwen2.5-1.5B via HuggingFace router (free, fast).
    Used for classification/formatting tasks that don't need a big model.
    """
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


def get_gemini_pro() -> LLM:
    return LLM(
        model="gemini/gemini-2.5-flash",
        api_key=settings.gemini_api_key,
        temperature=0.7,
        max_tokens=4096,
    )


def get_gemini_fast() -> LLM:
    return LLM(
        model="gemini/gemini-2.5-flash",
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
    Controlled by PRIMARY_LLM env var (default: huggingface — fully free).
    """
    global _primary_llm
    if _primary_llm is None:
        if _PRIMARY == "claude" and settings.anthropic_api_key:
            _primary_llm = get_claude()
        elif _PRIMARY == "gemini" and settings.gemini_api_key:
            _primary_llm = get_gemini_pro()
        else:
            _primary_llm = get_huggingface_primary()
    return _primary_llm


def fast() -> LLM:
    """Fast LLM for tone analysis, hashtag ranking, post assembly."""
    global _fast_llm
    if _fast_llm is None:
        if _PRIMARY == "gemini" and settings.gemini_api_key:
            _fast_llm = get_gemini_fast()
        else:
            _fast_llm = get_huggingface_fast()
    return _fast_llm


# Keep old names as aliases so nothing else breaks
def claude() -> LLM:
    return primary()


def gemini() -> LLM:
    return fast()
