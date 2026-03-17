from crewai import Agent
from app.agents.llm_config import primary


def get_image_selector() -> Agent:
    return Agent(
        role="Visual-Textual Coherence Judge",
        goal=(
            "Analyze all available image options (AI-generated and stock photos) and "
            "recommend the single best image for the LinkedIn post. Consider visual-textual "
            "coherence, professionalism, originality, and likely engagement impact. "
            "Return a JSON object with keys: recommended_id, ranking (ordered list of ids), "
            "rationale (2-3 sentences explaining why the recommended image is best)."
        ),
        backstory=(
            "You are a visual content director who has reviewed thousands of social media "
            "posts and their performance data. You know that the 'safe' choice is rarely the "
            "best choice — distinctive images outperform stock clichés. You evaluate images "
            "based on: relevance to post message, visual distinctiveness, professional quality, "
            "and emotional resonance. You always explain your reasoning so the human can "
            "override if they disagree."
        ),
        llm=primary(),
        verbose=True,
        max_iter=2,
        max_execution_time=30,
    )
