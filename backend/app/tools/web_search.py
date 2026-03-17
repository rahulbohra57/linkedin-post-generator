import os
from app.config import get_settings

settings = get_settings()


def get_web_search_tool():
    """
    Upgraded Tavily search: advanced depth, 10 results.
    Returns a crewai-compatible tool.
    Tries crewai_tools.TavilySearchResults first, falls back to
    langchain_tavily wrapped as a crewai BaseTool.
    """
    # Set env var so whichever library picks it up
    os.environ.setdefault("TAVILY_API_KEY", settings.tavily_api_key)

    try:
        from crewai_tools import TavilySearchResults
        return TavilySearchResults(
            max_results=10,
            search_depth="advanced",
            include_answer=True,
        )
    except (ImportError, Exception):
        pass

    try:
        from langchain_tavily import TavilySearch
        from crewai.tools import BaseTool
        from pydantic import BaseModel, Field

        class _SearchInput(BaseModel):
            query: str = Field(description="Search query")

        class TavilyTool(BaseTool):
            name: str = "web_search"
            description: str = "Search the web for up-to-date information on any topic."
            args_schema: type[BaseModel] = _SearchInput

            def _run(self, query: str) -> str:
                tool = TavilySearch(
                    max_results=10,
                    search_depth="advanced",
                    include_answer=True,
                )
                return str(tool.invoke(query))

        return TavilyTool()
    except Exception as e:
        raise RuntimeError(f"Could not initialize Tavily search tool: {e}")
