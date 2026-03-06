import re
import unicodedata
from typing import Any

from app.core.domain.pre_search import SearchCriteria


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFD", lowered)
    no_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", no_accents)


class DictionaryPreSearchExtractor:
    _part_patterns: list[tuple[str, tuple[str, ...]]] = [
        ("filtro de oleo", ("filtro de oleo", "filtro oleo")),
        ("filtro de ar", ("filtro de ar", "filtro ar")),
        ("filtro combustivel", ("filtro de combustivel", "filtro combustivel")),
        ("filtro", ("filtro",)),
        ("bandeja", ("bandeja", "bandenja", "bandeija")),
        ("pastilha de freio", ("pastilha de freio", "pastilha freio", "pastilha")),
        ("disco de freio", ("disco de freio", "disco freio")),
        ("amortecedor", ("amortecedor",)),
        ("coxim motor", ("coxim motor",)),
        ("coxim", ("coxim",)),
        ("bomba combustivel", ("bomba combustivel", "bomba de combustivel")),
        ("bomba d'agua", ("bomba dagua", "bomba d'agua", "bomba de agua")),
        ("rolamento roda", ("rolamento de roda", "rolamento roda")),
        ("farol", ("farol",)),
        ("correia dentada", ("correia dentada",)),
        ("kit correia", ("kit correia",)),
        ("retrovisor", ("retrovisor",)),
        ("sensor abs", ("sensor abs",)),
        ("radiador", ("radiador",)),
        ("parachoque", ("parachoque", "para choque")),
        ("vela ignicao", ("vela ignicao", "vela de ignicao", "velas ignicao")),
        ("motor arranque", ("motor arranque", "arranque")),
        ("bico injetor", ("bico injetor",)),
        ("kit embreagem", ("kit embreagem",)),
        ("embreagem", ("embreagem",)),
        ("lanterna traseira", ("lanterna traseira", "lanterna")),
    ]
    _model_aliases: dict[str, tuple[str, ...]] = {
        "EcoSport": ("ecosport",),
        "Fiesta": ("fiesta",),
        "Focus": ("focus",),
        "Gol": ("gol",),
        "Palio": ("palio",),
        "Uno": ("uno",),
        "Onix": ("onix",),
        "Corolla": ("corolla", "corola"),
        "Civic": ("civic",),
        "S10": ("s10",),
        "Hilux": ("hilux",),
    }

    def extract(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
    ) -> SearchCriteria:
        normalized_message = _normalize_text(message_text)
        normalized_context = self._build_context_text(last_messages)

        primary = self._extract_from(normalized_message, raw_text=message_text)
        fallback = self._extract_from(normalized_context, raw_text=normalized_context)
        return self._merge(primary=primary, fallback=fallback)

    def _extract_from(self, normalized_text: str, *, raw_text: str) -> SearchCriteria:
        return SearchCriteria(
            part_query=self._extract_part_query(normalized_text),
            part_code=self._extract_part_code(raw_text),
            vehicle_model=self._extract_vehicle_model(normalized_text),
            vehicle_year=self._extract_year(normalized_text),
            engine=self._extract_engine(normalized_text),
            side=self._extract_side(normalized_text),
            position=self._extract_position(normalized_text),
            quantity=self._extract_quantity(normalized_text),
        )

    @staticmethod
    def _merge(*, primary: SearchCriteria, fallback: SearchCriteria) -> SearchCriteria:
        return SearchCriteria(
            part_query=primary.part_query or fallback.part_query,
            part_code=primary.part_code or fallback.part_code,
            vehicle_model=primary.vehicle_model or fallback.vehicle_model,
            vehicle_year=primary.vehicle_year or fallback.vehicle_year,
            engine=primary.engine or fallback.engine,
            side=primary.side or fallback.side,
            position=primary.position or fallback.position,
            quantity=primary.quantity or fallback.quantity,
        )

    def _extract_part_query(self, text: str) -> str | None:
        for canonical, variations in self._part_patterns:
            if any(pattern in text for pattern in variations):
                return canonical
        return None

    def _extract_vehicle_model(self, text: str) -> str | None:
        for model, aliases in self._model_aliases.items():
            for alias in aliases:
                if re.search(rf"\b{re.escape(alias)}\b", text):
                    return model
        return None

    @staticmethod
    def _extract_year(text: str) -> int | None:
        match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _extract_engine(text: str) -> str | None:
        match = re.search(r"\b([1-6]\.[0-9])\b", text)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _extract_side(text: str) -> str | None:
        if re.search(r"\b(esq|esquerd[oa])\b", text):
            return "left"
        if re.search(r"\b(dir|direit[oa])\b", text):
            return "right"
        return None

    @staticmethod
    def _extract_position(text: str) -> str | None:
        if re.search(r"\b(diant|dianteir[oa])\b", text):
            return "front"
        if re.search(r"\b(tras|traseir[oa])\b", text):
            return "rear"
        return None

    @staticmethod
    def _extract_quantity(text: str) -> int | None:
        values = re.findall(r"\b(\d{1,3})\b", text)
        for raw in values:
            value = int(raw)
            if 1 <= value <= 50:
                return value
        return None

    @staticmethod
    def _extract_part_code(text: str) -> str | None:
        match = re.search(r"\b([A-Za-z]{2,5}[- ]?\d{3,8})\b", text or "")
        if not match:
            return None
        return match.group(1).upper().replace(" ", "-")

    @staticmethod
    def _build_context_text(last_messages: list[dict[str, Any]] | None) -> str:
        if not last_messages:
            return ""
        merged_text: list[str] = []
        for message in last_messages:
            text = str(message.get("text", "")).strip()
            if text:
                merged_text.append(text)
        return _normalize_text(" ".join(merged_text))
