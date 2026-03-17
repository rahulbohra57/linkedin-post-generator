"""
CrewAI pipeline orchestration.

Pipeline flow:
  research → tone_analysis → write → [edit ‖ hashtag_research] → assemble → pexels_keywords

After the crew finishes:
  - Gemini Flash verifies and refines the post text
  - pipeline_done event is emitted with the verified text

Progress events are pushed to the in-memory event bus and forwarded to the
client via WebSocket.
"""
import asyncio
import json
import re
import litellm
from crewai import Crew, Task, Process

from app.agents.definitions.researcher import get_researcher
from app.agents.definitions.tone_analyzer import get_tone_analyzer
from app.agents.definitions.writer import get_writer
from app.agents.definitions.editor import get_editor
from app.agents.definitions.hashtag_researcher import get_hashtag_researcher
from app.agents.definitions.post_assembler import get_post_assembler
from app.agents.definitions.image_prompt_generator import get_image_prompt_generator
from app.core.progress_emitter import (
    publish_event,
    make_agent_start_event,
    make_agent_complete_event,
    make_pipeline_done_event,
    make_error_event,
)


AGENT_ORDER = [
    "Researcher",
    "Tone Analyzer",
    "Writer",
    "Editor",
    "Hashtag Researcher",
    "Post Assembler",
    "Pexels Image Searcher",
    "Gemini Verifier",
]

WORD_TARGETS = {
    "short": 100,
    "medium": 200,
    "long": 300,
}


async def run_pipeline(
    session_id: str,
    topic: str,
    tone: str,
    target_audience: str,
    post_length: str,
) -> dict:
    """
    Run the full pipeline asynchronously.
    1. 7-agent CrewAI crew (research → assemble → pexels keywords)
    2. Gemini Flash verification of post text
    3. Emit pipeline_done with verified text
    Returns a dict with: post_text, hashtags, quality_score, quality_notes,
                         character_count, pexels_queries.
    """
    loop = asyncio.get_event_loop()

    def _run_crew_sync():
        return _build_and_run_crew(session_id, topic, tone, target_audience, post_length, loop)

    try:
        result = await loop.run_in_executor(None, _run_crew_sync)

        # Gemini verification step
        verified_text = await _gemini_verify(session_id, result["post_text"])
        result["post_text"] = verified_text

        # Emit final done event with verified text
        await publish_event(
            session_id,
            make_pipeline_done_event(
                result["post_text"], result["quality_score"], result["hashtags"]
            ),
        )

        return result
    except Exception as exc:
        await publish_event(session_id, make_error_event(str(exc)))
        raise


async def _gemini_verify(session_id: str, post_text: str) -> str:
    """
    Verify and refine the LinkedIn post text using the best available LLM.
    Uses Claude Haiku if available, otherwise falls back to Gemma.
    Emits agent_start / agent_complete events so the frontend shows progress.
    Falls back to the original text if all models are unavailable.
    """
    import os
    from app.config import get_settings
    settings = get_settings()

    await publish_event(session_id, make_agent_start_event("Gemini Verifier"))

    prompt_content = (
        "You are a senior LinkedIn content editor. Review the following LinkedIn post. "
        "Fix any grammatical errors, improve clarity and flow, and ensure it sounds "
        "authentic and human — not AI-generated. Keep the same structure, hashtags, "
        "and key insights. Do NOT add any explanation or commentary. "
        "Return ONLY the final post text.\n\n"
        f"Post:\n{post_text}"
    )

    # Try Claude Haiku first (reliable, no per-minute token limits)
    primary_llm = os.environ.get("PRIMARY_LLM", "gemma").lower()
    if primary_llm == "claude" and settings.anthropic_api_key:
        try:
            response = await litellm.acompletion(
                model="claude-haiku-4-5",
                api_key=settings.anthropic_api_key,
                messages=[{"role": "user", "content": prompt_content}],
                max_tokens=2048,
                temperature=0.3,
            )
            verified = response.choices[0].message.content.strip()
            await publish_event(session_id, make_agent_complete_event("Gemini Verifier", verified))
            return verified
        except Exception as e:
            # Fall through to Gemma
            pass

    # Fall back to Gemma if Gemini key available
    if not settings.gemini_api_key:
        await publish_event(
            session_id,
            make_agent_complete_event("Gemini Verifier", "Skipped (no API key configured)."),
        )
        return post_text

    try:
        response = await litellm.acompletion(
            model="gemini/gemma-3-4b-it",
            api_key=settings.gemini_api_key,
            messages=[{"role": "user", "content": prompt_content}],
            max_tokens=2048,
            temperature=0.3,
        )
        verified = response.choices[0].message.content.strip()
        await publish_event(session_id, make_agent_complete_event("Gemini Verifier", verified))
        return verified
    except Exception as e:
        await publish_event(
            session_id,
            make_agent_complete_event("Gemini Verifier", f"Verification skipped: {e}"),
        )
        return post_text


def _build_and_run_crew(
    session_id: str,
    topic: str,
    tone: str,
    target_audience: str,
    post_length: str,
    loop: asyncio.AbstractEventLoop,
) -> dict:
    """Synchronous crew execution (called from thread pool)."""

    word_target = WORD_TARGETS.get(post_length, 200)

    # --- Agents ---
    researcher = get_researcher()
    tone_analyzer = get_tone_analyzer()
    writer = get_writer()
    editor = get_editor()
    hashtag_researcher = get_hashtag_researcher()
    post_assembler = get_post_assembler()
    pexels_keyword_gen = get_image_prompt_generator()

    # --- Tasks ---
    research_task = Task(
        description=(
            f"Research the topic: '{topic}'. Find the latest facts, statistics, expert opinions, "
            f"and trends. Focus on information that would resonate with {target_audience} on LinkedIn. "
            f"Produce a structured research report with key insights, notable quotes or stats, "
            f"and recent developments."
        ),
        expected_output=(
            "A structured research report (500-800 words) covering: key facts, statistics, "
            "expert opinions, recent trends, and at least 3 specific insights that would "
            "interest LinkedIn professionals."
        ),
        agent=researcher,
        callback=lambda output: _emit(loop, session_id, "Researcher", str(output)),
    )

    tone_task = Task(
        description=(
            f"Based on the research report about '{topic}', analyze what tone and style "
            f"would work best for a LinkedIn post targeting '{target_audience}'. "
            f"The user's preferred tone is '{tone}'. Desired post length: {post_length} "
            f"(approximately {word_target} words). "
            f"Produce a tone brief specifying: tone adjectives, hook style, CTA style, "
            f"emoji density (none/low/medium), and reading level."
        ),
        expected_output=(
            "A tone brief with: tone (2-3 adjectives), hook_style (e.g., 'bold_statement', "
            "'question', 'story', 'statistic'), cta_style (e.g., 'question', 'challenge', "
            "'resource'), emoji_density ('none', 'low', 'medium'), word_target (number)."
        ),
        agent=tone_analyzer,
        context=[research_task],
        callback=lambda output: _emit(loop, session_id, "Tone Analyzer", str(output)),
    )

    write_task = Task(
        description=(
            f"Write a LinkedIn post about '{topic}' for {target_audience}. "
            f"Follow the tone brief exactly. Target approximately {word_target} words. "
            f"Structure: compelling hook (first 1-2 lines), valuable body content with "
            f"specific insights from the research, and a strong call-to-action. "
            f"Do NOT include hashtags — those will be added separately. "
            f"Write in a human, authentic voice — never generic or corporate."
        ),
        expected_output=(
            f"A complete LinkedIn post draft ({word_target} ± 30 words) with a hook, "
            f"body, and CTA. No hashtags. Human-sounding, engaging, and specific."
        ),
        agent=writer,
        context=[research_task, tone_task],
        callback=lambda output: _emit(loop, session_id, "Writer", str(output)),
    )

    edit_task = Task(
        description=(
            "Edit and polish the LinkedIn post draft. Improve clarity, rhythm, and impact. "
            "Ensure the first 2 lines (the hook) would make someone stop scrolling. "
            "Remove filler words and generic phrases. Tighten the CTA. "
            "Preserve the writer's voice and all key insights. Do NOT add hashtags."
        ),
        expected_output=(
            "A polished LinkedIn post with an improved hook, tighter body, and stronger CTA. "
            "No hashtags. Same approximate length as the draft."
        ),
        agent=editor,
        context=[write_task],
        callback=lambda output: _emit(loop, session_id, "Editor", str(output)),
    )

    hashtag_task = Task(
        description=(
            f"Research and select 5-7 optimal LinkedIn hashtags for a post about '{topic}' "
            f"targeting {target_audience}. Find hashtags that are relevant and have active "
            f"LinkedIn communities. Balance broad reach hashtags with niche discovery hashtags. "
            f"Return them as a space-separated string: #Tag1 #Tag2 #Tag3 ..."
        ),
        expected_output=(
            "A space-separated string of 5-7 hashtags starting with #. "
            "Example: #AIAgents #GenerativeAI #MachineLearning #LLM #TechLeadership"
        ),
        agent=hashtag_researcher,
        context=[research_task],
        callback=lambda output: _emit(loop, session_id, "Hashtag Researcher", str(output)),
    )

    assemble_task = Task(
        description=(
            "Combine the edited post body with the hashtags into a final LinkedIn post. "
            "Place hashtags on a new line at the end. Ensure total character count is under 3000. "
            "Verify proper line spacing (blank lines between paragraphs for LinkedIn readability). "
            "Score the post quality from 1-10 and provide 2-3 specific improvement notes. "
            "Return ONLY a valid JSON object with these exact keys: "
            "post_text (string), character_count (integer), quality_score (float), "
            "quality_notes (array of strings), hashtags (string)."
        ),
        expected_output=(
            'Valid JSON: {"post_text": "...", "character_count": 847, '
            '"quality_score": 8.5, "quality_notes": ["Strong hook", "CTA could be more specific"], '
            '"hashtags": "#GenAI #AIAgents"}'
        ),
        agent=post_assembler,
        context=[edit_task, hashtag_task],
        callback=lambda output: _emit(loop, session_id, "Post Assembler", str(output)),
    )

    pexels_task = Task(
        description=(
            f"Generate 3 Pexels stock photo search queries for a LinkedIn post about '{topic}'. "
            f"Query 1 style 'professional': workplace or industry scene related to the topic. "
            f"Query 2 style 'conceptual': abstract or metaphorical representation of the topic. "
            f"Query 3 style 'human_element': people interacting with the topic. "
            f"Keep each query to 2-5 words that work well as Pexels search terms. "
            f"Return ONLY a valid JSON array with 3 objects, each having keys: query, style."
        ),
        expected_output=(
            'Valid JSON array: [{"query": "ai technology office", "style": "professional"}, '
            '{"query": "digital innovation abstract", "style": "conceptual"}, '
            '{"query": "team collaboration workplace", "style": "human_element"}]'
        ),
        agent=pexels_keyword_gen,
        context=[assemble_task],
        callback=lambda output: _emit(loop, session_id, "Pexels Image Searcher", str(output)),
    )

    # --- Crew ---
    crew = Crew(
        agents=[
            researcher, tone_analyzer, writer, editor,
            hashtag_researcher, post_assembler, pexels_keyword_gen,
        ],
        tasks=[
            research_task, tone_task, write_task, edit_task,
            hashtag_task, assemble_task, pexels_task,
        ],
        process=Process.sequential,
        verbose=True,
    )

    # Emit pipeline start
    asyncio.run_coroutine_threadsafe(
        publish_event(session_id, {"event": "pipeline_start", "agents": AGENT_ORDER}),
        loop,
    ).result()

    crew.kickoff()

    # Extract assembled post from assemble_task output (NOT crew_output which is the last task)
    assembled_raw = str(assemble_task.output) if assemble_task.output else "{}"
    assembled = _extract_json(assembled_raw)

    # Extract Pexels search queries from pexels_task output
    pexels_raw = str(pexels_task.output) if pexels_task.output else "[]"
    pexels_queries = _extract_json_array(pexels_raw)

    post_text = assembled.get("post_text", assembled_raw)
    hashtags = assembled.get("hashtags", "")

    # Append hashtags only if the post doesn't already end with hashtag lines.
    # Checks the last non-empty line — avoids duplication when the assembler
    # already embedded hashtags inside post_text.
    non_empty_lines = [l for l in post_text.rstrip().splitlines() if l.strip()]
    post_ends_with_tags = bool(non_empty_lines and non_empty_lines[-1].strip().startswith("#"))
    if hashtags and not post_ends_with_tags:
        post_text = f"{post_text.rstrip()}\n\n{hashtags.strip()}"

    return {
        "post_text": post_text,
        "hashtags": hashtags,
        "quality_score": assembled.get("quality_score", 7.0),
        "quality_notes": assembled.get("quality_notes", []),
        "character_count": len(post_text),
        "pexels_queries": pexels_queries,
        # Keep image_prompts key for backward compat with session/images endpoint
        "image_prompts": pexels_queries,
    }


def _emit(loop: asyncio.AbstractEventLoop, session_id: str, agent_name: str, output: str):
    """Fire-and-forget event emit from sync context."""
    asyncio.run_coroutine_threadsafe(
        publish_event(session_id, make_agent_complete_event(agent_name, output)),
        loop,
    )


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from a string."""
    try:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}


def _extract_json_array(text: str) -> list:
    """Extract the first JSON array from a string."""
    try:
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return []
