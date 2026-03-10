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

    catalog_db_enabled: bool = Field(True, alias="CATALOG_DB_ENABLED")
    catalog_db_host: str = Field("presearch-db", alias="CATALOG_DB_HOST")
    catalog_db_port: int = Field(5432, alias="CATALOG_DB_PORT")
    catalog_db_name: str = Field("presearch", alias="CATALOG_DB_NAME")
    catalog_db_user: str = Field("presearch", alias="CATALOG_DB_USER")
    catalog_db_password: str = Field("presearch", alias="CATALOG_DB_PASSWORD")
    catalog_db_connect_timeout_s: int = Field(2, alias="CATALOG_DB_CONNECT_TIMEOUT_S")


@lru_cache
def get_settings() -> Settings:
    return Settings()
