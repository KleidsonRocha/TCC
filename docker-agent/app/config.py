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

    app_name: str = "docker-agent"
    app_env: str = Field("dev", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    agent_port: int = Field(8001, alias="AGENT_PORT")
    default_locale: str = Field("pt-BR", alias="DEFAULT_LOCALE")
    default_timezone: str = Field("America/Sao_Paulo", alias="DEFAULT_TIMEZONE")
    llm_base_url: str = Field("http://host.docker.internal:11434", alias="LLM_BASE_URL")
    llm_model: str = Field("qwen2.5:7b", alias="LLM_MODEL")
    llm_timeout_ms: int = Field(240000, alias="LLM_TIMEOUT_MS")
    llm_temperature: float = Field(0.0, alias="LLM_TEMPERATURE")
    llm_num_predict: int = Field(220, alias="LLM_NUM_PREDICT")
    llm_think: bool = Field(False, alias="LLM_THINK")
    llm_log_raw_response: bool = Field(False, alias="LLM_LOG_RAW_RESPONSE")
    llm_categories_file: str | None = Field(None, alias="LLM_CATEGORIES_FILE")


@lru_cache
def get_settings() -> Settings:
    return Settings()
