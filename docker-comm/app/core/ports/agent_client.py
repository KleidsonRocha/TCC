from typing import Protocol

from app.core.domain.models import AgentRequestPayload, AgentResponsePayload


class AgentClient(Protocol):
    async def send(
        self,
        payload: AgentRequestPayload,
        trace_id: str,
    ) -> tuple[AgentResponsePayload, int]:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

