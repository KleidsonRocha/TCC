from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "docker-comm"
    log_level: str = "INFO"

    agent_url: str = Field(..., alias="AGENT_URL")
    redis_url: str = Field(..., alias="REDIS_URL")

    default_branch_id: int = Field(1, alias="DEFAULT_BRANCH_ID")
    history_limit: int = Field(6, alias="HISTORY_LIMIT")
    session_ttl_seconds: int = Field(86400, alias="SESSION_TTL_SECONDS")

    agent_timeout_seconds: float = Field(20.0, alias="AGENT_TIMEOUT_SECONDS")
    agent_retry_count: int = Field(1, alias="AGENT_RETRY_COUNT")

    enable_test_endpoint: bool = Field(True, alias="ENABLE_TEST_ENDPOINT")
    api_key: str | None = Field(None, alias="API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
