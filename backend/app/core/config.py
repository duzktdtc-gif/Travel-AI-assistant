from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Travel AI Assistant"
    environment: str = "development"

    # Alibaba Cloud Model Studio / Qwen API
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"

    # Optional external APIs
    tavily_api_key: str | None = None
    serpapi_api_key: str | None = None
    openweather_api_key: str | None = None

    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()