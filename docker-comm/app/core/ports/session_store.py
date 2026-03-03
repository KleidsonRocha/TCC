from typing import Protocol

from app.core.domain.models import HistoryMessage


class SessionStore(Protocol):
    async def get_messages(self, conversation_id: str) -> list[HistoryMessage]:
        raise NotImplementedError

    async def append_messages(
        self,
        conversation_id: str,
        messages: list[HistoryMessage],
        history_limit: int,
    ) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

