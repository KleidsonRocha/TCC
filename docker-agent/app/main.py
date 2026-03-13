from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.respond import router as respond_router
from app.config import Settings, get_settings
from app.core.ports.pre_search_validator import PreSearchValidatorPort
from app.core.usecases.process_agent_request import ProcessAgentRequestUseCase
from app.infra.logger import configure_logging, get_logger
from app.infra.pre_search_catalog_pg import resolve_pre_search_catalog
from app.infra.pre_search_review_queue_pg import recorder_from_settings
from app.infra.pre_search_validator_llm import LLMPreSearchValidator
from app.infra.tools_mock import MockTools


def create_app(
    settings_override: Settings | None = None,
    pre_search_validator_override: PreSearchValidatorPort | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = settings_override or get_settings()
        configure_logging(settings.log_level)
        logger = get_logger()

        tools = MockTools()
        pre_search_validator = pre_search_validator_override
        if pre_search_validator is None:
            catalog = resolve_pre_search_catalog(settings=settings, logger=logger)
            pre_search_validator = LLMPreSearchValidator(
                settings=settings,
                logger=logger,
                catalog=catalog,
            )
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
            logger.info("service_stopped", extra={"service": settings.app_name})

    app = FastAPI(title="docker-agent", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(respond_router)
    return app


app = create_app()
