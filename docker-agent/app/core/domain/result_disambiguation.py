import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from app.core.domain.models import (
    PartItem,
    ResultCandidateState,
    ResultDisambiguationOption,
    ResultDisambiguationState,
)


RESULT_DISAMBIGUATION_SLOT = "result_disambiguation"
RESULT_DISAMBIGUATION_MAX_ATTEMPTS = 3
RESULT_DISAMBIGUATION_PAGE_SIZE = 10
DIRECT_RESULTS_LIMIT = 10
SEARCH_CANDIDATE_LIMIT = 50

_FIELD_PRIORITY = (
    "application",
    "variant",
    "engine",
    "side",
    "position",
    "axle",
    "injection",
    "transmission",
    "feature",
)
_FIELD_LABELS = {
    "application": "aplicacao",
    "variant": "versao",
    "engine": "motor",
    "side": "lado",
    "position": "posicao",
    "axle": "eixo",
    "injection": "injecao",
    "transmission": "transmissao",
    "feature": "caracteristica",
}
_HANDOFF_RE = re.compile(
    r"\b(?:atendente|atendimento humano|falar com (?:uma pessoa|alguem|vendedor)|vendedor)\b"
)
_NEGATION_RE = re.compile(
    r"^(?:nao|nenhum|nenhuma|nenhum desses|nenhuma dessas|outra|outro|nao sei|nao e nenhum)(?:\s+.*)?$"
)
_OPTION_NUMBER_RE = re.compile(r"^(?:opcao\s+|item\s+|a\s+)?(\d{1,2})$")
_NEXT_PAGE_RE = re.compile(
    r"^(?:ver\s+mais|mais|proximas?|proximas?\s+opcoes|outras?\s+opcoes)$"
)


@dataclass(frozen=True)
class ResultDisambiguationResolution:
    kind: Literal["selected", "listed", "ask", "rejected", "handoff", "unresolved"]
    listed_candidates: tuple[ResultCandidateState, ...] = ()
    state: ResultDisambiguationState | None = None
    selected_candidate: ResultCandidateState | None = None
    handoff_reason: str | None = None


def build_result_disambiguation_state(
    items: list[PartItem],
    *,
    attempt: int = 1,
    asked_fields: list[str] | None = None,
) -> ResultDisambiguationState:
    candidates = [
        ResultCandidateState(
            item_id=item.item_id,
            title=item.title,
            score=item.score,
            attributes={
                key: _unique_nonempty(values)
                for key, values in item.attributes.items()
                if _unique_nonempty(values)
            },
        )
        for item in items
    ]
    return _build_state_from_candidates(
        candidates,
        attempt=attempt,
        asked_fields=list(asked_fields or []),
    )


def resolve_result_disambiguation(
    message_text: str,
    state: ResultDisambiguationState,
) -> ResultDisambiguationResolution:
    normalized = _normalize(message_text)
    if _HANDOFF_RE.search(normalized):
        return ResultDisambiguationResolution(
            kind="handoff",
            handoff_reason="result_disambiguation_requested",
        )

    # Never interpret a negated code or attribute as a positive selection.
    direct_candidate = (
        None if re.search(r"\b(?:nao|nenhum|nenhuma)\b", normalized)
        else _match_candidate_by_code_or_title(normalized, state.candidates)
    )
    if direct_candidate is not None:
        return ResultDisambiguationResolution(
            kind="selected",
            selected_candidate=direct_candidate,
        )

    wants_next_page = bool(_NEXT_PAGE_RE.fullmatch(normalized))
    if wants_next_page or _NEGATION_RE.fullmatch(normalized):
        if state.question_key == "item":
            visible_ids = set(state.visible_candidate_ids)
            remaining = [
                candidate
                for candidate in state.candidates
                if candidate.item_id not in visible_ids
            ]
            if remaining:
                if len(remaining) <= DIRECT_RESULTS_LIMIT:
                    return ResultDisambiguationResolution(
                        kind="listed", listed_candidates=tuple(remaining)
                    )
                next_state = _build_state_from_candidates(
                    remaining,
                    attempt=state.attempt,
                    asked_fields=list(_FIELD_PRIORITY),
                    max_attempts=state.max_attempts,
                )
                return ResultDisambiguationResolution(kind="ask", state=next_state)
        return ResultDisambiguationResolution(kind="rejected")

    matched_option = (
        None if re.search(r"\b(?:nao|nenhum|nenhuma)\b", normalized)
        else _match_option(normalized, state.options)
    )
    if matched_option is not None:
        candidate_ids = set(matched_option.candidate_ids)
        filtered = [
            candidate
            for candidate in state.candidates
            if candidate.item_id in candidate_ids
        ]
        if len(filtered) == 1:
            return ResultDisambiguationResolution(
                kind="selected",
                selected_candidate=filtered[0],
            )
        if 1 < len(filtered) <= DIRECT_RESULTS_LIMIT:
            return ResultDisambiguationResolution(
                kind="listed", listed_candidates=tuple(filtered)
            )
        if filtered and state.attempt < state.max_attempts:
            next_state = _build_state_from_candidates(
                filtered,
                attempt=state.attempt + 1,
                asked_fields=[*state.asked_fields, state.question_key],
                max_attempts=state.max_attempts,
            )
            return ResultDisambiguationResolution(kind="ask", state=next_state)

    if state.attempt >= state.max_attempts:
        return ResultDisambiguationResolution(
            kind="handoff",
            handoff_reason="result_disambiguation_limit",
        )

    repeated_state = (
        _build_state_from_candidates(
            state.candidates,
            attempt=state.attempt + 1,
            asked_fields=[*state.asked_fields, state.question_key],
            max_attempts=state.max_attempts,
        )
        if state.question_key != "item"
        else state.model_copy(update={"attempt": state.attempt + 1})
    )
    return ResultDisambiguationResolution(kind="unresolved", state=repeated_state)


def is_handoff_request(message_text: str) -> bool:
    return bool(_HANDOFF_RE.search(_normalize(message_text)))


def _build_state_from_candidates(
    candidates: list[ResultCandidateState],
    *,
    attempt: int,
    asked_fields: list[str],
    max_attempts: int = RESULT_DISAMBIGUATION_MAX_ATTEMPTS,
) -> ResultDisambiguationState:
    field_name, options = _choose_discriminator(candidates, asked_fields=asked_fields)
    if field_name is not None:
        label = _FIELD_LABELS.get(field_name, field_name)
        values = "; ".join(option.label for option in options)
        prompt = f"Os resultados diferem em {label}: {values}. Qual opcao corresponde ao que voce procura?"
        return ResultDisambiguationState(
            candidates=candidates,
            question_key=field_name,
            prompt=prompt,
            options=options,
            asked_fields=asked_fields,
            visible_candidate_ids=[],
            attempt=attempt,
            max_attempts=max_attempts,
        )

    visible = candidates[:RESULT_DISAMBIGUATION_PAGE_SIZE]
    item_options = [
        ResultDisambiguationOption(
            label=f"{candidate.item_id} - {candidate.title}",
            candidate_ids=[candidate.item_id],
        )
        for candidate in visible
    ]
    return ResultDisambiguationState(
        candidates=candidates,
        question_key="item",
        prompt=(
            f"Encontrei {len(candidates)} opcoes compativeis. "
            "Veja os itens apresentados e, se quiser, informe um novo criterio"
            + (" ou responda 'ver mais'." if len(candidates) > len(visible) else ".")
        ),
        options=item_options,
        asked_fields=asked_fields,
        visible_candidate_ids=[candidate.item_id for candidate in visible],
        attempt=attempt,
        max_attempts=max_attempts,
    )


def _choose_discriminator(
    candidates: list[ResultCandidateState],
    *,
    asked_fields: list[str],
) -> tuple[str | None, list[ResultDisambiguationOption]]:
    best: tuple[tuple[float, int, int], str, list[ResultDisambiguationOption]] | None = None
    asked = set(asked_fields)
    total = max(len(candidates), 1)

    for priority_index, field_name in enumerate(_FIELD_PRIORITY):
        if field_name in asked:
            continue
        option_candidates: dict[str, list[str]] = {}
        labels: dict[str, str] = {}
        signatures: set[tuple[str, ...]] = set()
        covered = 0
        for candidate in candidates:
            values = _unique_nonempty(candidate.attributes.get(field_name, []))
            if not values:
                continue
            covered += 1
            normalized_values = [
                _normalize_directional_attribute(field_name, value)
                for value in values
            ]
            signatures.add(tuple(sorted(normalized_values)))
            for value in values:
                normalized_value = _normalize_directional_attribute(field_name, value)
                labels.setdefault(
                    normalized_value,
                    _public_directional_label(field_name, value),
                )
                option_candidates.setdefault(normalized_value, []).append(candidate.item_id)

        if len(signatures) < 2 or not 2 <= len(option_candidates) <= 6:
            continue
        # Missing data is not evidence of incompatibility. Every offered
        # answer must narrow the result set, including shared applications.
        if covered != total or any(len(ids) >= total for ids in option_candidates.values()):
            continue
        if any(len(value) > 80 for value in option_candidates):
            continue

        options = [
            ResultDisambiguationOption(label=labels[value], candidate_ids=ids)
            for value, ids in sorted(option_candidates.items(), key=lambda item: _normalize(item[0]))
        ]
        coverage = covered / total
        score = (coverage, len(signatures), -priority_index)
        if best is None or score > best[0]:
            best = (score, field_name, options)

    if best is None:
        return None, []
    return best[1], best[2]


def _match_option(
    normalized_message: str,
    options: list[ResultDisambiguationOption],
) -> ResultDisambiguationOption | None:
    number_match = _OPTION_NUMBER_RE.fullmatch(normalized_message)
    if number_match:
        index = int(number_match.group(1)) - 1
        if 0 <= index < len(options):
            return options[index]

    exact = [option for option in options if _normalize(option.label) == normalized_message]
    if len(exact) == 1:
        return exact[0]

    contained = [
        option
        for option in options
        if _contains_phrase(normalized_message, _normalize(option.label))
    ]
    return contained[0] if len(contained) == 1 else None


def _match_candidate_by_code_or_title(
    normalized_message: str,
    candidates: list[ResultCandidateState],
) -> ResultCandidateState | None:
    code_matches = [
        candidate
        for candidate in candidates
        if _contains_phrase(normalized_message, _normalize(candidate.item_id))
    ]
    if len(code_matches) == 1:
        return code_matches[0]

    title_matches = [
        candidate
        for candidate in candidates
        if _normalize(candidate.title) == normalized_message
    ]
    return title_matches[0] if len(title_matches) == 1 else None


def _contains_phrase(source: str, phrase: str) -> bool:
    if not phrase:
        return False
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", source))


def _unique_nonempty(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = " ".join(str(raw_value or "").strip().split())
        normalized = _normalize(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", str(value or "").strip().lower())
    without_accents = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return " ".join(without_accents.split())


def _normalize_directional_attribute(field_name: str, value: str) -> str:
    normalized = _normalize(value)
    if field_name == "side":
        if normalized in {"left", "esq", "esquerdo", "esquerda"}:
            return "esquerdo"
        if normalized in {"right", "dir", "direito", "direita"}:
            return "direito"
    if field_name in {"position", "axle"}:
        if normalized in {"front", "dianteiro", "dianteira", "diant", "eixo dianteiro", "eixo dianteira"}:
            return "dianteiro"
        if normalized in {"rear", "traseiro", "traseira", "tras", "eixo traseiro", "eixo traseira"}:
            return "traseiro"
    return normalized


def _public_directional_label(field_name: str, value: str) -> str:
    normalized = _normalize_directional_attribute(field_name, value)
    if field_name == "axle" and normalized in {"dianteiro", "traseiro"}:
        return f"Eixo {normalized}"
    if field_name in {"side", "position"} and normalized in {
        "esquerdo", "direito", "dianteiro", "traseiro",
    }:
        return normalized.capitalize()
    return value
