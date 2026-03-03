from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.test_send import router as test_send_router
from app.config import Settings, get_settings
from app.core.usecases.process_inbound_message import ProcessInboundMessageUseCase
from app.infra.agent_client_http import HttpAgentClient
from app.infra.logger import configure_logging, get_logger
from app.infra.session_store_redis import RedisSessionStore


def create_app(settings_override: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = settings_override or get_settings()
        configure_logging(settings.log_level)
        logger = get_logger()

        session_store = RedisSessionStore.from_url(settings.redis_url, settings)
        agent_client = HttpAgentClient(
            agent_url=settings.agent_url,
            timeout_seconds=settings.agent_timeout_seconds,
            retry_count=settings.agent_retry_count,
        )
        use_case = ProcessInboundMessageUseCase(
            session_store=session_store,
            agent_client=agent_client,
            settings=settings,
            logger=logger,
        )

        app.state.settings = settings
        app.state.logger = logger
        app.state.session_store = session_store
        app.state.agent_client = agent_client
        app.state.process_use_case = use_case

        logger.info(
            "service_started",
            extra={
                "service": settings.app_name,
                "agent_url": settings.agent_url,
                "history_limit": settings.history_limit,
            },
        )
        try:
            yield
        finally:
            await agent_client.close()
            await session_store.close()
            logger.info("service_stopped", extra={"service": settings.app_name})

    app = FastAPI(title="docker-comm", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(test_send_router, prefix="/test")
    return app


app = create_app()

