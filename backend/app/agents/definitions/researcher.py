from crewai import Agent
from app.agents.llm_config import primary
from app.tools.web_search import get_web_search_tool


def get_researcher() -> Agent:
    return Agent(
        role="Senior Research Analyst",
        goal=(
            "Find the most relevant, recent, and credible information about the given topic. "
            "Focus on facts, statistics, expert opinions, and trends that would resonate "
            "with LinkedIn professionals."
        ),
        backstory=(
            "You are an expert research analyst with 10+ years of experience synthesizing "
            "information from multiple sources. You know how to identify high-signal content "
            "and separate hype from substance. You always cross-reference sources and "
            "prioritize data-backed insights."
        ),
        tools=[get_web_search_tool()],
        llm=primary(),
        verbose=True,
        max_iter=5,
        max_execution_time=90,
    )
