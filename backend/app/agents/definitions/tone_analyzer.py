from crewai import Agent
from app.agents.llm_config import fast


def get_tone_analyzer() -> Agent:
    return Agent(
        role="LinkedIn Audience & Tone Strategy Expert",
        goal=(
            "Analyze the research content and user preferences to define the exact tone, "
            "style, and structural approach the LinkedIn post should take. Output a clear "
            "tone brief that the Writer agent will follow precisely."
        ),
        backstory=(
            "You are a content strategy expert specializing in LinkedIn audience psychology. "
            "You have studied thousands of viral LinkedIn posts and understand how tone, "
            "hook style, and call-to-action approach vary dramatically by audience type. "
            "You know that a post for CTOs sounds completely different from one for new grads, "
            "even on the same topic."
        ),
        llm=fast(),
        verbose=True,
        max_iter=3,
        max_execution_time=45,
    )
