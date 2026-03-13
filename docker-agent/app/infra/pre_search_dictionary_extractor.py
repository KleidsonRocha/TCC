import re
import unicodedata
from typing import Any

from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.pre_search import SearchCriteria
from app.infra.pre_search_part_code import (
    compile_part_code_patterns,
    is_valid_part_code_candidate,
    normalize_part_code_candidate,
)


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFD", lowered)
    no_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", no_accents)


class DictionaryPreSearchExtractor:
    def __init__(self, *, catalog: PreSearchCatalog) -> None:
        self._part_patterns = list(catalog.part_patterns)
        self._brand_aliases = dict(catalog.brand_aliases)
        self._model_aliases = dict(catalog.model_aliases)
        self._part_code_patterns = compile_part_code_patterns(catalog.part_code_patterns)

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
        vehicle_brand = self._extract_vehicle_brand(normalized_text)
        vehicle_model = self._extract_vehicle_model(normalized_text)
        vehicle_year = self._extract_year(normalized_text)
        return SearchCriteria(
            part_query=self._extract_part_query(normalized_text),
            part_code=self._extract_part_code(
                raw_text,
                vehicle_brand=vehicle_brand,
                vehicle_model=vehicle_model,
                vehicle_year=vehicle_year,
            ),
            vehicle_brand=vehicle_brand,
            vehicle_model=vehicle_model,
            vehicle_year=vehicle_year,
            engine=self._extract_engine(normalized_text),
            side=self._extract_side(normalized_text),
            position=self._extract_position(normalized_text),
            axle=self._extract_axle(normalized_text),
            quantity=self._extract_quantity(normalized_text),
        )

    @staticmethod
    def _merge(*, primary: SearchCriteria, fallback: SearchCriteria) -> SearchCriteria:
        return SearchCriteria(
            part_query=primary.part_query or fallback.part_query,
            part_code=primary.part_code or fallback.part_code,
            vehicle_brand=primary.vehicle_brand or fallback.vehicle_brand,
            vehicle_model=DictionaryPreSearchExtractor._merge_vehicle_model(
                primary.vehicle_model,
                fallback.vehicle_model,
            ),
            vehicle_year=primary.vehicle_year or fallback.vehicle_year,
            engine=primary.engine or fallback.engine,
            side=primary.side or fallback.side,
            position=primary.position or fallback.position,
            axle=primary.axle or fallback.axle,
            variant=primary.variant or fallback.variant,
            quantity=primary.quantity or fallback.quantity,
        )

    @staticmethod
    def _merge_vehicle_model(primary: str | None, fallback: str | None) -> str | None:
        if primary and not DictionaryPreSearchExtractor._is_year_like_model(primary):
            return primary
        return fallback or primary

    @staticmethod
    def _is_year_like_model(value: str | None) -> bool:
        return bool(re.fullmatch(r"(19\d{2}|20\d{2})", str(value or "").strip()))

    def _extract_part_query(self, text: str) -> str | None:
        best_canonical: str | None = None
        best_match_len = -1
        for canonical, variations in self._part_patterns:
            for pattern in variations:
                candidate = str(pattern or "").strip()
                if not candidate:
                    continue
                if not re.search(rf"\b{re.escape(candidate)}\b", text):
                    continue
                if len(candidate) > best_match_len:
                    best_match_len = len(candidate)
                    best_canonical = canonical
        return best_canonical

    def _extract_vehicle_model(self, text: str) -> str | None:
        best_match: tuple[int, int, int] | None = None
        best_model: str | None = None
        for model, aliases in self._model_aliases.items():
            for alias in aliases:
                candidate = str(alias or "").strip()
                if not candidate:
                    continue
                if not re.search(rf"\b{re.escape(candidate)}\b", text):
                    continue

                score = self._model_alias_score(candidate)
                if best_match is None or score > best_match:
                    best_match = score
                    best_model = model
        return best_model

    def _extract_vehicle_brand(self, text: str) -> str | None:
        for brand, aliases in self._brand_aliases.items():
            for alias in aliases:
                if re.search(rf"\b{re.escape(alias)}\b", text):
                    return brand
        return None

    @staticmethod
    def _extract_year(text: str) -> int | None:
        match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _model_alias_score(alias: str) -> tuple[int, int, int]:
        alias_text = str(alias or "").strip()
        has_letters = 1 if re.search(r"[a-zA-Z]", alias_text) else 0
        is_year_token = 1 if re.fullmatch(r"(19\d{2}|20\d{2})", alias_text) else 0
        return (
            has_letters,
            0 if is_year_token else 1,
            len(alias_text),
        )

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
    def _extract_axle(text: str) -> str | None:
        if re.search(r"\b(eixo dianteir[oa]|eixo diant)\b", text):
            return "front"
        if re.search(r"\b(eixo traseir[oa]|eixo tras)\b", text):
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

    def _extract_part_code(
        self,
        text: str,
        *,
        vehicle_brand: str | None,
        vehicle_model: str | None,
        vehicle_year: int | None,
    ) -> str | None:
        for pattern in self._part_code_patterns:
            for match in pattern.finditer(text or ""):
                candidate = normalize_part_code_candidate(match.group(0))
                if not is_valid_part_code_candidate(
                    candidate,
                    compiled_patterns=self._part_code_patterns,
                    vehicle_brand=vehicle_brand,
                    vehicle_model=vehicle_model,
                    vehicle_year=vehicle_year,
                ):
                    continue
                return candidate
        return None

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
