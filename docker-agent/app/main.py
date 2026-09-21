import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.respond import router as respond_router
from app.api.routes.review import router as review_router
from app.config import Settings, get_settings
from app.core.ports.pre_search_validator import PreSearchValidatorPort
from app.core.ports.tools import ToolsPort
from app.core.ports.pre_search_review_repository import PreSearchReviewRepositoryPort
from app.core.usecases.process_agent_request import ProcessAgentRequestUseCase
from app.infra.erp_search_tools_pg import resolve_search_tools
from app.infra.logger import configure_logging, get_logger
from app.infra.pre_search_catalog_pg import resolve_pre_search_catalog
from app.infra.pre_search_review_queue_pg import recorder_from_settings
from app.infra.pre_search_review_admin_pg import review_repository_from_settings
from app.infra.pre_search_validator_llm import LLMPreSearchValidator


def _validate_production_security(settings: Settings) -> None:
    if not settings.is_production:
        return
    missing = [
        name
        for name, value in (
            ("REVIEW_API_KEY", settings.review_api_key),
            ("RESPOND_GATEWAY_API_KEY", settings.respond_gateway_api_key),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Configuracao de seguranca obrigatoria em producao ausente: "
            + ", ".join(missing)
        )


def create_app(
    settings_override: Settings | None = None,
    pre_search_validator_override: PreSearchValidatorPort | None = None,
    tools_override: ToolsPort | None = None,
    review_repository_override: PreSearchReviewRepositoryPort | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = settings_override or get_settings()
        _validate_production_security(settings)
        configure_logging(settings.log_level)
        logger = get_logger()

        catalog = None
        pre_search_validator = pre_search_validator_override
        if pre_search_validator is None:
            catalog = resolve_pre_search_catalog(settings=settings, logger=logger)
            pre_search_validator = LLMPreSearchValidator(
                settings=settings,
                logger=logger,
                catalog=catalog,
            )
        tools = tools_override or resolve_search_tools(settings=settings, logger=logger, catalog=catalog)
        use_case = ProcessAgentRequestUseCase(
            tools=tools,
            pre_search_validator=pre_search_validator,
            settings=settings,
            logger=logger,
            review_recorder=recorder_from_settings(settings=settings, logger=logger),
        )

        app.state.settings = settings
        app.state.logger = logger
        app.state.tools = tools
        app.state.pre_search_validator = pre_search_validator
        app.state.process_use_case = use_case
        app.state.review_repository = review_repository_override or review_repository_from_settings(
            settings=settings
        )

        warmup_task: asyncio.Task[None] | None = None
        warmup = getattr(pre_search_validator, "warmup", None)
        if settings.llm_warmup_enabled and callable(warmup):
            async def run_warmup() -> None:
                try:
                    logger.info(
                        "pre_search_llm_warmup_started",
                        extra={"model": settings.llm_model},
                    )
                    await asyncio.to_thread(warmup)
                except Exception:
                    logger.warning(
                        "pre_search_llm_warmup_failed",
                        extra={"model": settings.llm_model},
                        exc_info=True,
                    )

            warmup_task = asyncio.create_task(run_warmup())

        logger.info(
            "service_started",
            extra={
                "service": settings.app_name,
                "app_env": settings.app_env,
                "agent_port": settings.agent_port,
                "pre_search_validator": pre_search_validator.__class__.__name__,
            },
        )
        try:
            yield
        finally:
            if warmup_task is not None:
                warmup_task.cancel()
                with suppress(asyncio.CancelledError):
                    await warmup_task
            logger.info("service_stopped", extra={"service": settings.app_name})

    app = FastAPI(title="docker-agent", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(respond_router)
    app.include_router(review_router)
    return app


app = create_app()
