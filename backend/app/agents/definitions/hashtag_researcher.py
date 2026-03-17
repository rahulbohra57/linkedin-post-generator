from crewai import Agent
from app.agents.llm_config import fast
from app.tools.web_search import get_web_search_tool


def get_hashtag_researcher() -> Agent:
    return Agent(
        role="LinkedIn SEO and Hashtag Specialist",
        goal=(
            "Research and select the most effective LinkedIn hashtags for the given topic. "
            "Find hashtags that have active communities but are not so broad that the post "
            "gets lost. Return exactly 5-7 hashtags ranked by expected reach and relevance. "
            "Format output as a space-separated hashtag string: #Tag1 #Tag2 #Tag3"
        ),
        backstory=(
            "You are a LinkedIn SEO specialist who has studied hashtag performance across "
            "thousands of posts. You know that #AI has 10M+ followers but posts get buried "
            "instantly, while #GenerativeAI gets better engagement for AI-specific content. "
            "You always balance reach (large hashtags) with discoverability (niche hashtags). "
            "You research what hashtags top voices in each industry actually use."
        ),
        tools=[get_web_search_tool()],
        llm=fast(),
        verbose=True,
        max_iter=4,
        max_execution_time=60,
    )
