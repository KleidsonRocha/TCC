from fastapi import Request

from app.config import Settings
from app.core.usecases.process_agent_request import ProcessAgentRequestUseCase


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_process_agent_request_use_case(request: Request) -> ProcessAgentRequestUseCase:
    return request.app.state.process_use_case
