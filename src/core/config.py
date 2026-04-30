from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Andela MCP Assessment API"
    log_level: str = "debug"

    backend_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    openai_api_key: str | None = None
    openai_model: str = "gpt-5-nano"

    mcp_server_url: str = "https://order-mcp-74afyau24q-uc.a.run.app/mcp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
