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
    if settings.review_api_key and x_review_key != settings.review_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid review API key.")
