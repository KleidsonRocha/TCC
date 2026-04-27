import re
from dataclasses import dataclass
from typing import Any

from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.pre_search import SearchCriteria
from app.infra.pre_search_text import normalize_pre_search_text
from app.infra.pre_search_part_code import (
    compile_part_code_patterns,
    is_valid_part_code_candidate,
    normalize_part_code_candidate,
)


@dataclass(frozen=True)
class _AliasCandidate:
    canonical: str
    alias: str
    token_count: int
    char_count: int


@dataclass(frozen=True)
class _ScoredAliasCandidate:
    candidate: _AliasCandidate
    similarity: float
    distance: int


class DictionaryPreSearchExtractor:
    _MIN_FUZZY_TOKEN_LENGTH = 4
    _SINGLE_TOKEN_FUZZY_GAP = 0.05
    _MULTI_TOKEN_FUZZY_GAP = 0.03

    def __init__(self, *, catalog: PreSearchCatalog) -> None:
        self._part_patterns = list(catalog.part_patterns)
        self._brand_aliases = dict(catalog.brand_aliases)
        self._model_aliases = dict(catalog.model_aliases)
        self._part_code_patterns = compile_part_code_patterns(catalog.part_code_patterns)
        self._part_alias_candidates = self._build_alias_candidates(self._part_patterns)
        self._max_part_alias_tokens = max(
            (candidate.token_count for candidate in self._part_alias_candidates),
            default=1,
        )

    def extract(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
    ) -> SearchCriteria:
        normalized_message = normalize_pre_search_text(message_text)
        normalized_context = self._build_context_text(last_messages)

        primary = self._extract_from(normalized_message, raw_text=message_text)
        fallback = self._extract_from(normalized_context, raw_text=normalized_context)
        return self._merge(primary=primary, fallback=fallback)

    def canonicalize_part_query(self, value: str | None) -> str | None:
        normalized_value = normalize_pre_search_text(value)
        if not normalized_value:
            return None
        return self._extract_part_query(normalized_value)

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
        exact_match = self._extract_exact_part_query_match(text)
        fuzzy_match = self._extract_fuzzy_part_query_match(text)
        if exact_match and fuzzy_match:
            if self._should_prefer_fuzzy_part_match(
                exact_match=exact_match,
                fuzzy_match=fuzzy_match,
            ):
                return fuzzy_match.candidate.canonical
            return exact_match.canonical
        if exact_match:
            return exact_match.canonical
        if fuzzy_match:
            return fuzzy_match.candidate.canonical
        return None

    def _extract_exact_part_query_match(self, text: str) -> _AliasCandidate | None:
        best_match: _AliasCandidate | None = None
        for candidate in self._part_alias_candidates:
            if not re.search(rf"\b{re.escape(candidate.alias)}\b", text):
                continue
            if best_match is None or (
                candidate.token_count,
                candidate.char_count,
            ) > (
                best_match.token_count,
                best_match.char_count,
            ):
                best_match = candidate
        return best_match

    def _extract_fuzzy_part_query_match(self, text: str) -> _ScoredAliasCandidate | None:
        tokens = self._tokenize(text)
        if not tokens or not self._part_alias_candidates:
            return None

        windows_by_size = self._build_token_windows(
            tokens=tokens,
            max_window_size=self._max_part_alias_tokens,
        )
        best_by_canonical: dict[str, _ScoredAliasCandidate] = {}

        for candidate in self._part_alias_candidates:
            candidate_windows = windows_by_size.get(candidate.token_count, ())
            if not candidate_windows:
                continue
            best_score_for_alias: _ScoredAliasCandidate | None = None
            for window in candidate_windows:
                score = self._score_part_alias_window(candidate=candidate, window=window)
                if score is None:
                    continue
                scored_candidate = _ScoredAliasCandidate(
                    candidate=candidate,
                    similarity=score[0],
                    distance=-score[1],
                )
                if best_score_for_alias is None or self._scored_alias_sort_key(
                    scored_candidate
                ) > self._scored_alias_sort_key(best_score_for_alias):
                    best_score_for_alias = scored_candidate
            if best_score_for_alias is None:
                continue

            current_best = best_by_canonical.get(candidate.canonical)
            if current_best is None or self._scored_alias_sort_key(
                best_score_for_alias
            ) > self._scored_alias_sort_key(current_best):
                best_by_canonical[candidate.canonical] = best_score_for_alias

        if not best_by_canonical:
            return None

        ranked = sorted(
            best_by_canonical.values(),
            key=self._scored_alias_sort_key,
            reverse=True,
        )
        best_score = ranked[0]
        if len(ranked) > 1:
            second_score = ranked[1]
            min_gap = (
                self._MULTI_TOKEN_FUZZY_GAP
                if best_score.candidate.token_count > 1
                else self._SINGLE_TOKEN_FUZZY_GAP
            )
            if (best_score.similarity - second_score.similarity) < min_gap:
                return None
        return best_score

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
            role = str(message.get("role", "")).strip().lower()
            if role and role != "user":
                continue
            text = str(message.get("text", "")).strip()
            if text:
                merged_text.append(text)
        return normalize_pre_search_text(" ".join(merged_text))

    @staticmethod
    def _build_alias_candidates(
        part_patterns: list[tuple[str, tuple[str, ...]]],
    ) -> tuple[_AliasCandidate, ...]:
        candidates: list[_AliasCandidate] = []
        seen: set[tuple[str, str]] = set()
        for canonical, aliases in part_patterns:
            canonical_text = str(canonical or "").strip().lower()
            if not canonical_text:
                continue
            for alias in aliases:
                alias_text = str(alias or "").strip().lower()
                if not alias_text:
                    continue
                key = (canonical_text, alias_text)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    _AliasCandidate(
                        canonical=canonical_text,
                        alias=alias_text,
                        token_count=len(alias_text.split()),
                        char_count=len(alias_text),
                    )
                )
        return tuple(sorted(candidates, key=lambda item: (item.token_count, item.char_count), reverse=True))

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token for token in re.findall(r"[a-z0-9]+", text or "") if token]

    @classmethod
    def _build_token_windows(
        cls,
        *,
        tokens: list[str],
        max_window_size: int,
    ) -> dict[int, tuple[str, ...]]:
        windows: dict[int, list[str]] = {}
        if not tokens:
            return {}
        upper_bound = max(1, min(max_window_size, len(tokens)))
        for window_size in range(1, upper_bound + 1):
            values = [
                " ".join(tokens[start : start + window_size])
                for start in range(0, len(tokens) - window_size + 1)
            ]
            windows[window_size] = values
        return {size: tuple(values) for size, values in windows.items()}

    @classmethod
    def _score_part_alias_window(
        cls,
        *,
        candidate: _AliasCandidate,
        window: str,
    ) -> tuple[float, int, int] | None:
        if not window or window == candidate.alias:
            return None
        if candidate.char_count < cls._MIN_FUZZY_TOKEN_LENGTH:
            return None
        if len(window) < cls._MIN_FUZZY_TOKEN_LENGTH:
            return None
        if not cls._matching_initials(candidate.alias, window):
            return None

        max_distance = cls._max_part_alias_distance(candidate)
        if abs(candidate.char_count - len(window)) > max_distance:
            return None

        distance = cls._damerau_levenshtein_distance(candidate.alias, window)
        if distance <= 0 or distance > max_distance:
            return None

        similarity = 1.0 - (distance / max(candidate.char_count, len(window)))
        min_similarity = cls._min_part_alias_similarity(candidate)
        if similarity < min_similarity:
            return None

        return (round(similarity, 4), -distance, candidate.token_count)

    @staticmethod
    def _matching_initials(alias: str, window: str) -> bool:
        alias_tokens = alias.split()
        window_tokens = window.split()
        if len(alias_tokens) != len(window_tokens):
            return False
        return all(
            alias_token and window_token and alias_token[0] == window_token[0]
            for alias_token, window_token in zip(alias_tokens, window_tokens)
        )

    @staticmethod
    def _max_part_alias_distance(candidate: _AliasCandidate) -> int:
        if candidate.token_count > 1:
            return 2 if candidate.char_count <= 14 else 3
        if candidate.char_count <= 5:
            return 1
        return 2

    @staticmethod
    def _min_part_alias_similarity(candidate: _AliasCandidate) -> float:
        if candidate.token_count > 1:
            return 0.84 if candidate.char_count <= 14 else 0.8
        if candidate.char_count <= 5:
            return 0.8
        return 0.82

    @staticmethod
    def _should_prefer_fuzzy_part_match(
        *,
        exact_match: _AliasCandidate,
        fuzzy_match: _ScoredAliasCandidate,
    ) -> bool:
        fuzzy_candidate = fuzzy_match.candidate
        if fuzzy_match.similarity < 0.9:
            return False
        if fuzzy_candidate.token_count > exact_match.token_count:
            return True
        return fuzzy_candidate.char_count >= (exact_match.char_count + 4)

    @staticmethod
    def _scored_alias_sort_key(match: _ScoredAliasCandidate) -> tuple[float, int, int, int]:
        return (
            match.similarity,
            -match.distance,
            match.candidate.token_count,
            match.candidate.char_count,
        )

    @staticmethod
    def _damerau_levenshtein_distance(left: str, right: str) -> int:
        left_text = str(left or "")
        right_text = str(right or "")
        if left_text == right_text:
            return 0
        if not left_text:
            return len(right_text)
        if not right_text:
            return len(left_text)

        previous_previous_row: list[int] | None = None
        previous_row = list(range(len(right_text) + 1))

        for left_index, left_char in enumerate(left_text, start=1):
            current_row = [left_index]
            for right_index, right_char in enumerate(right_text, start=1):
                insertion = current_row[right_index - 1] + 1
                deletion = previous_row[right_index] + 1
                substitution = previous_row[right_index - 1] + (0 if left_char == right_char else 1)
                current = min(insertion, deletion, substitution)

                if (
                    previous_previous_row is not None
                    and left_index > 1
                    and right_index > 1
                    and left_char == right_text[right_index - 2]
                    and left_text[left_index - 2] == right_char
                ):
                    current = min(current, previous_previous_row[right_index - 2] + 1)

                current_row.append(current)
            previous_previous_row = previous_row
            previous_row = current_row

        return previous_row[-1]
