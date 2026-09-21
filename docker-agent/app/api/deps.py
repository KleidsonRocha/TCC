import secrets

from fastapi import Header, HTTPException, Request, status

from app.config import Settings
from app.core.usecases.process_agent_request import ProcessAgentRequestUseCase
from app.core.ports.pre_search_review_repository import PreSearchReviewRepositoryPort


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_process_agent_request_use_case(request: Request) -> ProcessAgentRequestUseCase:
    return request.app.state.process_use_case


def get_pre_search_review_repository(request: Request) -> PreSearchReviewRepositoryPort:
    return request.app.state.review_repository


def require_review_api_key(
    request: Request,
    x_review_key: str | None = Header(default=None, alias="X-Review-Key"),
) -> None:
    settings: Settings = get_settings(request)
    if settings.review_api_key and not secrets.compare_digest(
        x_review_key or "", settings.review_api_key
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid review API key.")


def require_respond_gateway_key(
    *,
    request: Request,
    x_agent_gateway_key: str | None,
) -> None:
    """Protect caller-supplied history/state when a gateway key is configured."""
    settings: Settings = get_settings(request)
    expected_key = settings.respond_gateway_api_key
    if expected_key is None:
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gateway state authentication is not configured.",
            )
        return
    if not secrets.compare_digest(x_agent_gateway_key or "", expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent gateway key.",
        )
