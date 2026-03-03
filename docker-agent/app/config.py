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


@lru_cache
def get_settings() -> Settings:
    return Settings()
