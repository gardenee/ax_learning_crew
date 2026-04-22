from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "local"
    app_name: str = "menu-agent"

    database_url: str = "postgresql+psycopg://app:app@postgres:5432/menu_agent"

    qdrant_url: str = "http://qdrant:6333"

    model_id: str = "claude-sonnet-4-5-20250929"
    anthropic_api_key: str | None = None

    max_tool_turns: int = 8
    agent_timeout_seconds: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
