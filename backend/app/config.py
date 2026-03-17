from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLMs
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    huggingfacehub_api_token: str = ""
    openai_api_key: str = ""

    # Search & Images
    tavily_api_key: str = ""
    pexels_api_key: str = ""

    # LinkedIn OAuth
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8000/api/auth/linkedin/callback"

    # Infrastructure
    database_url: str = "sqlite+aiosqlite:///./linkedin_posts.db"
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    local_storage_path: str = "./storage/images"

    # App
    secret_key: str = "change-me-in-production"
    environment: str = "development"
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
