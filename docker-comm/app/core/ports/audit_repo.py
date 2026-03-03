from typing import Any, Protocol


class AuditRepository(Protocol):
    async def write_event(self, event: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError

