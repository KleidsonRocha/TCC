from typing import Protocol

from app.core.domain.models import PartItem


class ToolsPort(Protocol):
    def search_parts(self, query: str, branch_id: int) -> list[PartItem]:
        raise NotImplementedError
