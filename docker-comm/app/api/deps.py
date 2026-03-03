from fastapi import Header, HTTPException, Request, status

from app.config import Settings
from app.core.usecases.process_inbound_message import ProcessInboundMessageUseCase


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_process_inbound_message_use_case(request: Request) -> ProcessInboundMessageUseCase:
    return request.app.state.process_use_case


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    settings: Settings = get_settings(request)
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

