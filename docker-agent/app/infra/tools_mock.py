import unicodedata

from app.core.domain.models import PartItem
from app.core.ports.tools import ToolsPort


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


class MockTools(ToolsPort):
    def search_parts(self, query: str, branch_id: int) -> list[PartItem]:
        print(f"[mock_search_parts] branch_id={branch_id} query='{query}'")
        normalized_query = _normalize_text(query)

        if "bandeja" in normalized_query:
            return [
                PartItem(item_id="BDJ-001", title="Bandeja dianteira lado esquerdo", score=0.91),
                PartItem(item_id="BDJ-002", title="Bandeja dianteira lado direito", score=0.89),
            ]

        if "filtro de oleo" in normalized_query:
            return [
                PartItem(item_id="FLT-010", title="Filtro de oleo motor 1.6", score=0.96),
            ]

        if "coxim" in normalized_query:
            return [
                PartItem(item_id="CXM-101", title="Coxim do motor dianteiro", score=0.92),
            ]

        return []
