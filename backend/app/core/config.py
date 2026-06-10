from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Travel AI Assistant"
    environment: str = "development"

    # Google AI Studio / Gemini API key. LangChain reads GOOGLE_API_KEY.
    google_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    # Optional external APIs. The app runs with demo fallback data if these are empty.
    tavily_api_key: str | None = None
    serpapi_api_key: str | None = None
    openweather_api_key: str | None = None

    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
