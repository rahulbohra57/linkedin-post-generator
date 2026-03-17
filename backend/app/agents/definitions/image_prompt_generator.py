from crewai import Agent
from app.agents.llm_config import fast


def get_image_prompt_generator() -> Agent:
    return Agent(
        role="Pexels Image Search Specialist",
        goal=(
            "Generate exactly 3 distinct Pexels stock photo search queries for the LinkedIn post. "
            "Each query should target a different visual angle: professional/workplace, conceptual/abstract, "
            "and human/people-focused. "
            "Return ONLY a valid JSON array with 3 objects, each having keys: 'query' (2-5 word search term) "
            "and 'style' (one of: professional, conceptual, human_element). "
            "Queries must be concise and work well as Pexels search terms."
        ),
        backstory=(
            "You are a visual content curator who selects the perfect stock photos for LinkedIn posts. "
            "You know exactly which search terms return high-quality, relevant images on Pexels. "
            "You never suggest generating AI images — you find great existing photos that perfectly "
            "complement professional content."
        ),
        llm=fast(),
        verbose=True,
        max_iter=2,
        max_execution_time=30,
    )
