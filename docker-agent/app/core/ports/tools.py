from typing import Protocol

from app.core.domain.models import PartItem
from app.core.domain.pre_search import SearchCriteria


class ToolsPort(Protocol):
    def search_parts(
        self,
        query: str,
        branch_id: int,
        criteria: SearchCriteria | None = None,
    ) -> list[PartItem]:
        raise NotImplementedError
