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
    llm_max_concurrent_requests: int = Field(
        2, alias="LLM_MAX_CONCURRENT_REQUESTS"
    )
    llm_temperature: float = Field(0.0, alias="LLM_TEMPERATURE")
    llm_num_predict: int = Field(220, alias="LLM_NUM_PREDICT")
    llm_keep_alive: str | None = Field("1h", alias="LLM_KEEP_ALIVE")
    llm_warmup_enabled: bool = Field(True, alias="LLM_WARMUP_ENABLED")
    llm_think: bool = Field(False, alias="LLM_THINK")
    llm_log_raw_response: bool = Field(False, alias="LLM_LOG_RAW_RESPONSE")
    llm_categories_file: str | None = Field(None, alias="LLM_CATEGORIES_FILE")
    pre_search_deterministic_bypass_enabled: bool = Field(
        True,
        alias="PRE_SEARCH_DETERMINISTIC_BYPASS_ENABLED",
    )
    pre_search_deterministic_ask_enabled: bool = Field(
        True,
        alias="PRE_SEARCH_DETERMINISTIC_ASK_ENABLED",
    )

    catalog_db_enabled: bool = Field(True, alias="CATALOG_DB_ENABLED")
    catalog_db_host: str = Field("presearch-db", alias="CATALOG_DB_HOST")
    catalog_db_port: int = Field(5432, alias="CATALOG_DB_PORT")
    catalog_db_name: str = Field("presearch", alias="CATALOG_DB_NAME")
    catalog_db_user: str = Field("presearch", alias="CATALOG_DB_USER")
    catalog_db_password: str = Field("presearch", alias="CATALOG_DB_PASSWORD")
    catalog_db_connect_timeout_s: int = Field(2, alias="CATALOG_DB_CONNECT_TIMEOUT_S")
    erp_db_enabled: bool = Field(False, alias="ERP_DB_ENABLED")
    erp_db_host: str = Field("localhost", alias="ERP_DB_HOST")
    erp_db_port: int = Field(5432, alias="ERP_DB_PORT")
    erp_db_name: str = Field("soccol", alias="ERP_DB_NAME")
    erp_db_user: str = Field("postgres", alias="ERP_DB_USER")
    erp_db_password: str = Field("", alias="ERP_DB_PASSWORD")
    erp_db_connect_timeout_s: int = Field(2, alias="ERP_DB_CONNECT_TIMEOUT_S")
    erp_search_timeout_ms: int = Field(10000, alias="ERP_SEARCH_TIMEOUT_MS")
    erp_search_max_concurrent_requests: int = Field(
        4, alias="ERP_SEARCH_MAX_CONCURRENT_REQUESTS"
    )
    erp_fallback_db_enabled: bool = Field(True, alias="ERP_FALLBACK_DB_ENABLED")
    pre_search_review_capture_enabled: bool = Field(True, alias="PRE_SEARCH_REVIEW_CAPTURE_ENABLED")
    review_api_key: str | None = Field(None, alias="REVIEW_API_KEY")
    ft_dataset_slug: str = Field("pre-search-ft-v1", alias="FT_DATASET_SLUG")
    ft_target_model_prefix: str = Field("pre-search-qwen2.5-ft", alias="FT_TARGET_MODEL_PREFIX")
    ft_golden_set_file: str = Field(
        "docs/assets/datasets/pre_search_num_predict_golden_set.json",
        alias="FT_GOLDEN_SET_FILE",
    )
    ft_train_command: str | None = Field(None, alias="FT_TRAIN_COMMAND")
    ft_publish_command: str | None = Field(None, alias="FT_PUBLISH_COMMAND")
    ft_active_env_file: str = Field(".env", alias="FT_ACTIVE_ENV_FILE")
    ft_ollama_base_model: str = Field("qwen2.5:7b", alias="FT_OLLAMA_BASE_MODEL")
    ft_ollama_artifact_kind: str = Field("adapter", alias="FT_OLLAMA_ARTIFACT_KIND")
    ft_ollama_artifact_path: str | None = Field(None, alias="FT_OLLAMA_ARTIFACT_PATH")
    ft_ollama_output_dir: str = Field(".tmp/ollama_models", alias="FT_OLLAMA_OUTPUT_DIR")


@lru_cache
def get_settings() -> Settings:
    return Settings()
