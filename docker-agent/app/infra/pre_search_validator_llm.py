import json
import logging
import re
import time
from copy import deepcopy
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.core.domain.part_code import (
    has_literal_part_code_evidence,
    normalize_part_code_candidate,
)
from app.core.domain.models import ConversationState
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.errors import PreSearchServiceUnavailableError
from app.core.domain.pre_search import NextQuestion, PreSearchValidation, SearchCriteria
from app.core.ports.pre_search_validator import PreSearchValidatorPort
from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor
from app.infra.pre_search_part_code import (
    compile_part_code_patterns,
    is_valid_part_code_candidate,
)
from app.infra.pre_search_text import normalize_pre_search_text

DEFAULT_CRITERIA_WEIGHTS: dict[str, int] = {
    "part_code": 100,
    "part_query": 45,
    "vehicle_model": 35,
    "vehicle_year": 20,
    "vehicle_brand": 15,
    "engine": 20,
    "side": 10,
    "position": 10,
    "axle": 10,
    "variant": 10,
    "quantity": 5,
}
DEFAULT_MIN_SCORE_TO_SEARCH = 70
RUNTIME_MIN_SCORE_TO_SEARCH_BY_PART: dict[str, int] = {
    "lubrificantes": 55,
}
# These are conservative safeguards for common Brazilian vehicle names while
# older catalog imports still classify some models as SEM_MARCA_MAPEADA.  The
# database relation, when present, always takes precedence.
MODEL_BRAND_FALLBACKS: dict[str, set[str]] = {
    "gol": {"volkswagen", "vw"},
    "golf": {"volkswagen", "vw"},
    "voyage": {"volkswagen", "vw"},
    "saveiro": {"volkswagen", "vw"},
    "fox": {"volkswagen", "vw"},
    "polo": {"volkswagen", "vw"},
    "ecosport": {"ford"},
    "focus": {"ford"},
}
VEHICLE_OPTIONAL_PART_QUERIES: set[str] = {
    "lubrificantes",
}
SCORING_FIELD_PRIORITY: tuple[str, ...] = (
    "part_code",
    "part_query",
    "vehicle_model",
    "vehicle_year",
    "engine",
    "vehicle_brand",
    "side",
    "position",
    "axle",
    "variant",
    "quantity",
)
DETERMINISTIC_ASK_FIELD_PRIORITY: tuple[str, ...] = (
    "part_query",
    "vehicle_model",
    "vehicle_year",
    "engine",
    "side",
    "position",
    "axle",
    "variant",
)
COXIM_TYPE_SLOT = "coxim_type"
COXIM_GENERAL_FAMILY = "coxins"
COXIM_AMORTECEDOR_FAMILY = "coxim amortecedor"
DETERMINISTIC_ASK_PART_REQUEST_PATTERN = re.compile(
    r"\b(?:quero|preciso|procuro|busco|tem|teria|gostaria)\b"
    r"[^.!?]{0,40}\b(?:peca|pecas|autopeca|autopecas|item automotivo)\b"
)
DETERMINISTIC_ASK_GENERIC_PART_TOKENS: set[str] = {
    "autopeca",
    "autopecas",
    "automotivo",
    "item",
}
DETERMINISTIC_ASK_UNSAFE_INTENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "handoff_intent",
        re.compile(
            r"\b(?:atendente|atendimento humano|falar com (?:um )?vendedor|"
            r"chamar (?:um )?vendedor|transferir|humano)\b"
        ),
    ),
    (
        "subject_change",
        re.compile(
            r"\b(?:mudei de ideia|mudando de assunto|outro assunto|"
            r"esquece|esqueca|deixa pra la|agora quero outra|outra peca)\b"
        ),
    ),
    (
        "functional_description",
        re.compile(
            r"\b(?:aquilo que|coisa que|peca que|serve para|responsavel por|"
            r"que segura|que evita|que faz)\b"
        ),
    ),
    (
        "symptom_description",
        re.compile(
            r"\b(?:barulho|rangendo|vibrando|pulando|vazando|falhando|"
            r"quebrado|quebrada|nao funciona|nao liga|esquentando)\b"
        ),
    ),
)
RUNTIME_SEARCH_RULE_OVERRIDES: dict[str, dict[str, bool]] = {
    "bandeja": {
        "needs_side": True,
        "needs_position": False,
        "needs_axle": False,
    },
    "bandejas": {
        "needs_side": True,
        "needs_position": False,
        "needs_axle": False,
    },
    "disco de freio": {
        "needs_position": True,
    },
    "discos de freio": {
        "needs_position": True,
    },
}
UNSUPPORTED_PART_HANDOFF_PROMPT = (
    "Essa familia de peca nao esta no catalogo para pesquisa automatica. "
    "Vou encaminhar para atendimento humano."
)
UNSUPPORTED_PART_STOPWORDS: set[str] = {
    "a",
    "agora",
    "ajuda",
    "bom",
    "boa",
    "carro",
    "cotacao",
    "da",
    "de",
    "dia",
    "do",
    "e",
    "favor",
    "me",
    "meu",
    "minha",
    "no",
    "noite",
    "o",
    "ola",
    "orcamento",
    "parte",
    "para",
    "peca",
    "pode",
    "por",
    "preco",
    "preciso",
    "procuro",
    "pro",
    "qual",
    "quero",
    "tarde",
    "tem",
    "tenho",
    "um",
    "uma",
    "valor",
    "veiculo",
    "vc",
    "vcs",
    "voce",
    "voces",
}


@dataclass(frozen=True)
class DeterministicAskEligibility:
    eligible: bool
    reason: str
    criteria: SearchCriteria
    missing_fields: tuple[str, ...] = ()
    next_question: NextQuestion | None = None


class LLMPreSearchValidator(PreSearchValidatorPort):
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        catalog: PreSearchCatalog,
    ) -> None:
        self._logger = logger
        self._base_url = settings.llm_base_url.rstrip("/")
        self._model = settings.llm_model
        self._timeout = max(settings.llm_timeout_ms, 1000) / 1000
        self._temperature = settings.llm_temperature
        self._num_predict = max(settings.llm_num_predict, 64)
        self._keep_alive = self._normalize_keep_alive(settings.llm_keep_alive)
        self._think = settings.llm_think
        self._log_raw_response = settings.llm_log_raw_response
        self._categories_text = self._load_categories_text(settings.llm_categories_file)
        self._invalid_slot_tokens = set(catalog.invalid_slot_tokens)
        self._generic_ambiguous_parts = set(catalog.generic_ambiguous_parts)
        self._known_group_terms = set(catalog.known_group_terms)
        self._needs_side = set(catalog.needs_side)
        self._needs_position = set(catalog.needs_position)
        self._needs_axle = set(catalog.needs_axle)
        self._needs_engine = set(catalog.needs_engine)
        self._needs_variant = set(catalog.needs_variant)
        self._engine_by_model = {
            str(model).lower(): list(options)
            for model, options in catalog.engine_by_model.items()
        }
        self._engine_options_by_model = {
            str(model).lower(): list(options)
            for model, options in catalog.engine_options_by_model.items()
        }
        self._model_brands = {
            normalize_pre_search_text(model): {
                normalize_pre_search_text(brand)
                for brand in brands
                if normalize_pre_search_text(brand)
            }
            for model, brands in catalog.model_brands.items()
        }
        self._part_code_patterns = compile_part_code_patterns(catalog.part_code_patterns)
        self._criteria_weights = self._normalize_criteria_weights(catalog.criteria_weights)
        self._min_score_to_search = max(int(catalog.min_score_to_search), 0)
        self._min_score_to_search_by_part = self._normalize_part_min_score_overrides(
            catalog.min_score_to_search_by_part
        )
        for part_query, score in RUNTIME_MIN_SCORE_TO_SEARCH_BY_PART.items():
            self._min_score_to_search_by_part.setdefault(part_query, score)
        self._dictionary_extractor = DictionaryPreSearchExtractor(catalog=catalog)
        self._apply_runtime_search_rule_overrides()
        self._last_audit_info: ContextVar[dict[str, Any] | None] = ContextVar(
            "pre_search_last_audit_info",
            default=None,
        )

    def get_last_audit(self) -> dict[str, Any] | None:
        audit_info = self._last_audit_info.get()
        if audit_info is None:
            return None
        return deepcopy(audit_info)

    def runtime_diagnostics(self) -> dict[str, Any]:
        return {
            "base_url": self._base_url,
            "model": self._model,
            "timeout_s": self._timeout,
        }

    def _apply_runtime_search_rule_overrides(self) -> None:
        for part_name, overrides in RUNTIME_SEARCH_RULE_OVERRIDES.items():
            normalized_part = str(part_name or "").strip().lower()
            if not normalized_part:
                continue
            self._set_rule_requirement(self._needs_side, normalized_part, overrides.get("needs_side"))
            self._set_rule_requirement(self._needs_position, normalized_part, overrides.get("needs_position"))
            self._set_rule_requirement(self._needs_axle, normalized_part, overrides.get("needs_axle"))
            self._set_rule_requirement(self._needs_engine, normalized_part, overrides.get("needs_engine"))
            self._set_rule_requirement(self._needs_variant, normalized_part, overrides.get("needs_variant"))

    @staticmethod
    def _set_rule_requirement(target: set[str], part_name: str, required: bool | None) -> None:
        if required is None:
            return
        if required:
            target.add(part_name)
            return
        target.discard(part_name)

    def extract_dictionary_seed_criteria(
        self,
        *,
        message_text: str,
        last_messages: list[dict[str, Any]] | None = None,
    ) -> SearchCriteria:
        return self._dictionary_extractor.extract(
            message_text,
            last_messages=last_messages or [],
        )

    def extract_items(self, message_text: str) -> list[SearchCriteria]:
        """Expose conservative multi-item extraction to the use case."""
        return self._dictionary_extractor.extract_items(message_text)

    def build_score_policy(self, *, dictionary_seed_criteria: SearchCriteria) -> dict[str, Any]:
        canonical_seed_criteria = self._canonicalize_criteria_part_query(
            dictionary_seed_criteria
        )
        return self._build_llm_score_policy(
            dictionary_seed_criteria=canonical_seed_criteria
        )

    def build_system_prompt(self) -> str:
        return self._build_system_instructions(categories_text=self._categories_text)

    def canonicalize_part_query(self, value: str | None) -> str | None:
        return self._canonicalize_part_query(value)

    def validate_item_for_search(
        self,
        criteria: SearchCriteria,
        *,
        message_text: str,
        last_messages: list[dict[str, Any]] | None = None,
    ) -> PreSearchValidation:
        """Apply the same deterministic search gate to one multi-item row.

        ``items`` returned by the LLM are only candidates.  Each row must be
        canonicalized and independently proven before it can reach the ERP;
        attributes and a part-code from another row cannot satisfy this gate.
        """
        values = criteria.model_dump(exclude_none=False)
        values["part_query"] = self._canonicalize_part_query(values.get("part_query"))

        part_code = normalize_part_code_candidate(values.get("part_code"))
        explicit_part_code = bool(
            part_code
            and has_literal_part_code_evidence(
                part_code,
                message_text=message_text,
                last_messages=last_messages,
            )
            and self._looks_like_part_code(
                part_code,
                vehicle_brand=values.get("vehicle_brand"),
                vehicle_model=values.get("vehicle_model"),
                vehicle_year=values.get("vehicle_year"),
            )
        )
        values["part_code"] = part_code if explicit_part_code else None
        item_criteria = SearchCriteria.model_validate(values)

        missing_fields = self._resolve_missing_fields(
            criteria=item_criteria,
            llm_missing_fields=[],
            include_rule_fields=True,
            explicit_part_code=explicit_part_code,
        )
        score_explicit_fields = self._build_score_explicit_fields(
            dictionary_criteria=item_criteria,
        )
        criteria_score = self._calculate_criteria_score(
            item_criteria,
            score_explicit_fields=score_explicit_fields,
        )

        if explicit_part_code:
            return PreSearchValidation(
                decision="search",
                criteria=item_criteria,
                missing_fields=[],
                next_question=None,
                confidence=0.99,
            )

        if not missing_fields and self._score_threshold_applies(item_criteria):
            if criteria_score < self._min_score_to_search_for(item_criteria):
                missing_fields = self._resolve_missing_fields(
                    criteria=item_criteria,
                    llm_missing_fields=self._calculate_score_gap_missing_fields(
                        criteria=item_criteria,
                        current_missing_fields=[],
                        score_explicit_fields=score_explicit_fields,
                    ),
                    include_rule_fields=True,
                )

        if not missing_fields:
            return PreSearchValidation(
                decision="search",
                criteria=item_criteria,
                missing_fields=[],
                next_question=None,
                confidence=0.99,
            )

        next_question = self._build_default_next_question(
            criteria=item_criteria,
            missing_fields=missing_fields,
        )
        return PreSearchValidation(
            decision="ask",
            criteria=item_criteria,
            missing_fields=missing_fields,
            next_question=next_question,
            confidence=0.99,
        )

    def evaluate_deterministic_ask_eligibility(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
        conversation_state: ConversationState | None = None,
    ) -> DeterministicAskEligibility:
        """Evaluate the conservative policy without calling the LLM.

        The runtime method consumes this result only when every eligibility
        condition and the backend-governed question are available.
        """

        _ = last_messages
        current_criteria = self._normalize_pending_follow_up_current_criteria(
            message_text=message_text,
            criteria=self._canonicalize_criteria_part_query(
                self._dictionary_extractor.extract(message_text, last_messages=[])
            ),
            conversation_state=conversation_state,
        )

        coxim_eligibility = self._evaluate_coxim_type_eligibility(
            message_text=message_text,
            current_criteria=current_criteria,
            conversation_state=conversation_state,
        )
        if coxim_eligibility is not None:
            return coxim_eligibility

        is_follow_up = self._is_deterministic_follow_up_candidate(
            current_criteria=current_criteria,
            conversation_state=conversation_state,
        )
        if conversation_state and conversation_state.pending_slot:
            if not is_follow_up:
                return self._deterministic_ask_ineligible(
                    reason="active_pending_slot",
                    criteria=current_criteria,
                )
            contextual_criteria = self._dictionary_extractor.extract(
                message_text,
                last_messages=last_messages,
            )
            contextual_criteria = self._apply_pending_follow_up_answer_to_context(
                criteria=contextual_criteria,
                current_criteria=current_criteria,
                conversation_state=conversation_state,
                message_text=message_text,
            )
            current_criteria = self._merge_dictionary_with_conversation_state(
                dictionary_criteria=contextual_criteria,
                conversation_state=conversation_state,
            )

        unsafe_reason = self._deterministic_ask_unsafe_intent_reason(message_text)
        if unsafe_reason:
            return self._deterministic_ask_ineligible(
                reason=unsafe_reason,
                criteria=current_criteria,
            )

        if current_criteria.part_code:
            return self._deterministic_ask_ineligible(
                reason="part_code_present",
                criteria=current_criteria,
            )

        part_query = self._canonicalize_part_query(current_criteria.part_query)
        exact_part_query = bool(
            part_query
            and part_query not in self._generic_ambiguous_parts
            and self._dictionary_extractor.has_exact_part_query_match(
                message_text=message_text,
                canonical_part_query=part_query,
            )
        )

        # A short answer to a governed question (for example, "2008" after
        # asking the year) does not repeat the part family. The family is
        # already proven by the active ConversationState, so requiring it in
        # the current message would send an otherwise deterministic follow-up
        # back to the LLM.
        if is_follow_up and part_query and part_query not in self._generic_ambiguous_parts:
            exact_part_query = True

        if part_query and not exact_part_query:
            return self._deterministic_ask_ineligible(
                reason="part_query_not_exact",
                criteria=current_criteria,
            )

        if not part_query:
            if not self._is_explicit_generic_part_request(message_text):
                return self._deterministic_ask_ineligible(
                    reason="part_request_not_explicit",
                    criteria=current_criteria,
                )
            unresolved_tokens = set(
                self._non_catalog_part_candidate_tokens(
                    criteria=current_criteria,
                    message_text=message_text,
                    last_messages=[],
                )
            ) - DETERMINISTIC_ASK_GENERIC_PART_TOKENS
            if unresolved_tokens:
                return self._deterministic_ask_ineligible(
                    reason="unresolved_part_description",
                    criteria=current_criteria,
                )

        missing_fields = self._order_deterministic_ask_fields(
            self._calculate_missing_fields(
                current_criteria,
                explicit_part_code=False,
            )
        )
        if not missing_fields:
            return self._deterministic_ask_ineligible(
                reason="no_missing_field",
                criteria=current_criteria,
            )

        next_question = self._build_default_next_question(
            criteria=current_criteria,
            missing_fields=missing_fields,
        )
        if not next_question or next_question.key != missing_fields[0]:
            return self._deterministic_ask_ineligible(
                reason="question_not_governed_by_backend",
                criteria=current_criteria,
            )

        return DeterministicAskEligibility(
            eligible=True,
            reason=(
                "complete_follow_up_missing_field"
                if is_follow_up
                else (
                    "exact_family_missing_field"
                    if exact_part_query
                    else "explicit_generic_part_request"
                )
            ),
            criteria=current_criteria,
            missing_fields=tuple(missing_fields),
            next_question=next_question,
        )

    def try_validate_deterministic_ask(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
        conversation_state: ConversationState | None = None,
    ) -> PreSearchValidation | None:
        self._last_audit_info.set(None)
        safety_result = self._request_safety_confirmation(
            message_text=message_text,
            criteria=self._dictionary_extractor.extract(message_text, last_messages=[]),
        )
        if safety_result is not None:
            self._set_deterministic_safety_audit(safety_result)
            return safety_result

        eligibility = self.evaluate_deterministic_ask_eligibility(
            message_text,
            last_messages=last_messages,
            conversation_state=conversation_state,
        )
        if (
            not eligibility.eligible
            or not eligibility.missing_fields
            or eligibility.next_question is None
        ):
            return None

        self._last_audit_info.set({
            "llm_endpoint_used": None,
            "llm_raw_content": None,
            "llm_output_valid": None,
            "llm_parse_error": None,
            "llm_fallback_used": None,
            "llm_decision_raw": None,
            "pre_search_path": "deterministic_ask",
            "deterministic_reason": eligibility.reason,
            "missing_fields": list(eligibility.missing_fields),
            "next_question_key": eligibility.next_question.key,
        })
        return PreSearchValidation(
            decision="ask",
            criteria=eligibility.criteria,
            missing_fields=list(eligibility.missing_fields),
            next_question=eligibility.next_question,
            confidence=0.99,
        )

    @staticmethod
    def _deterministic_ask_ineligible(
        *,
        reason: str,
        criteria: SearchCriteria,
    ) -> DeterministicAskEligibility:
        return DeterministicAskEligibility(
            eligible=False,
            reason=reason,
            criteria=criteria,
        )

    @staticmethod
    def _deterministic_ask_unsafe_intent_reason(message_text: str) -> str | None:
        normalized_text = normalize_pre_search_text(message_text)
        for reason, pattern in DETERMINISTIC_ASK_UNSAFE_INTENT_PATTERNS:
            if pattern.search(normalized_text):
                return reason
        return None

    @staticmethod
    def _is_explicit_generic_part_request(message_text: str) -> bool:
        return bool(
            DETERMINISTIC_ASK_PART_REQUEST_PATTERN.search(
                normalize_pre_search_text(message_text)
            )
        )

    @staticmethod
    def _order_deterministic_ask_fields(missing_fields: list[str]) -> list[str]:
        deduped = {
            str(field_name or "").strip()
            for field_name in missing_fields
            if str(field_name or "").strip()
        }
        return sorted(
            deduped,
            key=lambda field_name: (
                DETERMINISTIC_ASK_FIELD_PRIORITY.index(field_name)
                if field_name in DETERMINISTIC_ASK_FIELD_PRIORITY
                else len(DETERMINISTIC_ASK_FIELD_PRIORITY),
                field_name,
            ),
        )

    def try_validate_deterministically(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
        conversation_state: ConversationState | None = None,
    ) -> PreSearchValidation | None:
        self._last_audit_info.set(None)
        context = last_messages or []
        current_criteria = self._normalize_pending_follow_up_current_criteria(
            message_text=message_text,
            criteria=self._dictionary_extractor.extract(
                message_text,
                last_messages=[],
            ),
            conversation_state=conversation_state,
        )
        resolved_coxim_type = self._resolve_pending_coxim_type(
            message_text=message_text,
            conversation_state=conversation_state,
        )
        trusted_coxim_resolution = resolved_coxim_type is not None
        if resolved_coxim_type is not None:
            current_criteria = resolved_coxim_type
        if self._request_safety_confirmation(
            message_text=message_text,
            criteria=current_criteria,
        ) is not None:
            return None
        is_follow_up = trusted_coxim_resolution or self._is_deterministic_follow_up_candidate(
            current_criteria=current_criteria,
            conversation_state=conversation_state,
        )

        if conversation_state and conversation_state.pending_slot and not is_follow_up:
            return None

        if trusted_coxim_resolution:
            criteria = current_criteria
            bypass_reason = "coxim_type_follow_up"
        elif is_follow_up:
            dictionary_criteria = self._dictionary_extractor.extract(
                message_text,
                last_messages=context,
            )
            dictionary_criteria = self._apply_pending_follow_up_answer_to_context(
                criteria=dictionary_criteria,
                current_criteria=current_criteria,
                conversation_state=conversation_state,
                message_text=message_text,
            )
            criteria = self._merge_dictionary_with_conversation_state(
                dictionary_criteria=dictionary_criteria,
                conversation_state=conversation_state,
            )
            bypass_reason = "complete_follow_up"
        else:
            criteria = self._canonicalize_criteria_part_query(current_criteria)
            bypass_reason = "complete_request"

        explicit_part_code = bool(criteria.part_code)
        if not trusted_coxim_resolution and not self._deterministic_identity_is_trusted(
            message_text=message_text,
            criteria=criteria,
            conversation_state=conversation_state,
            is_follow_up=is_follow_up,
        ):
            return None

        missing_fields = self._calculate_missing_fields(
            criteria,
            explicit_part_code=explicit_part_code,
        )
        if missing_fields:
            return None

        score_explicit_fields = self._build_score_explicit_fields(
            dictionary_criteria=criteria,
        )
        criteria_score = self._calculate_criteria_score(
            criteria,
            score_explicit_fields=score_explicit_fields,
        )
        if (
            self._score_threshold_applies(
                criteria,
                explicit_part_code=explicit_part_code,
            )
            and criteria_score < self._min_score_to_search_for(criteria)
        ):
            return None

        self._last_audit_info.set({
            "llm_endpoint_used": None,
            "llm_raw_content": None,
            "llm_output_valid": None,
            "llm_parse_error": None,
            "llm_fallback_used": None,
            "llm_decision_raw": None,
            "pre_search_path": "deterministic_bypass",
            "deterministic_reason": bypass_reason,
            "criteria_score": criteria_score,
            "min_score_to_search": self._min_score_to_search_for(criteria),
        })
        return PreSearchValidation(
            decision="search",
            criteria=criteria,
            missing_fields=[],
            next_question=None,
            confidence=0.99,
        )

    @staticmethod
    def _coxim_type_question(criteria: SearchCriteria) -> DeterministicAskEligibility:
        return DeterministicAskEligibility(
            eligible=True,
            reason="coxim_type_required",
            criteria=criteria,
            missing_fields=(COXIM_TYPE_SLOT,),
            next_question=NextQuestion(
                key=COXIM_TYPE_SLOT,
                prompt="O coxim é do motor/câmbio ou do amortecedor?",
                options=["Motor/câmbio", "Coxim do amortecedor", "Não sei"],
            ),
        )

    def _evaluate_coxim_type_eligibility(
        self,
        *,
        message_text: str,
        current_criteria: SearchCriteria,
        conversation_state: ConversationState | None,
    ) -> DeterministicAskEligibility | None:
        if conversation_state and conversation_state.pending_slot == COXIM_TYPE_SLOT:
            resolved = self._resolve_pending_coxim_type(
                message_text=message_text,
                conversation_state=conversation_state,
            )
            if resolved is None:
                return self._coxim_type_question(conversation_state.criteria)
            missing_fields = self._order_deterministic_ask_fields(
                self._calculate_missing_fields(resolved, explicit_part_code=False)
            )
            if not missing_fields:
                return self._deterministic_ask_ineligible(
                    reason="coxim_type_complete",
                    criteria=resolved,
                )
            return DeterministicAskEligibility(
                eligible=True,
                reason="coxim_type_resolved_missing_field",
                criteria=resolved,
                missing_fields=tuple(missing_fields),
                next_question=self._build_default_next_question(
                    criteria=resolved,
                    missing_fields=missing_fields,
                ),
            )

        part_query = self._canonicalize_part_query(current_criteria.part_query)
        normalized = normalize_pre_search_text(message_text)
        if (
            part_query == COXIM_GENERAL_FAMILY
            and not re.search(r"\b(?:motor|cambio|amortecedor)\b", normalized)
        ):
            return self._coxim_type_question(current_criteria)
        return None

    def _resolve_pending_coxim_type(
        self,
        *,
        message_text: str,
        conversation_state: ConversationState | None,
    ) -> SearchCriteria | None:
        if not conversation_state or conversation_state.pending_slot != COXIM_TYPE_SLOT:
            return None
        normalized = normalize_pre_search_text(message_text)
        target: str | None = None
        if re.search(r"\bamortecedor(?:es)?\b", normalized):
            target = COXIM_AMORTECEDOR_FAMILY
        elif re.search(r"\b(?:motor|cambio)\b", normalized):
            target = COXIM_GENERAL_FAMILY
        if target is None:
            return None
        values = conversation_state.criteria.model_dump(exclude_none=False)
        values["part_query"] = self._canonicalize_part_query(target) or target
        return SearchCriteria.model_validate(values)

    @staticmethod
    def _is_deterministic_follow_up_candidate(
        *,
        current_criteria: SearchCriteria,
        conversation_state: ConversationState | None,
    ) -> bool:
        if not conversation_state or not conversation_state.pending_slot:
            return False
        if conversation_state.last_decision != "ask":
            return False

        pending_slot = str(conversation_state.pending_slot or "").strip()
        if pending_slot not in SearchCriteria.model_fields:
            return False
        if pending_slot == "axle" and current_criteria.position:
            return True
        value = getattr(current_criteria, pending_slot, None)
        if isinstance(value, str):
            return bool(value.strip())
        return value is not None

    @staticmethod
    def _is_year_only_follow_up_answer(message_text: str) -> bool:
        normalized = normalize_pre_search_text(message_text)
        return bool(re.fullmatch(r"(?:ano\s+)?(?:19\d{2}|20\d{2})", normalized))

    @staticmethod
    def _is_direction_only_follow_up_answer(message_text: str) -> bool:
        normalized = normalize_pre_search_text(message_text)
        return normalized in {
            "dianteiro",
            "dianteira",
            "traseiro",
            "traseira",
            "eixo dianteiro",
            "eixo dianteira",
            "eixo traseiro",
            "eixo traseira",
            "front",
            "rear",
        }

    def _normalize_pending_follow_up_current_criteria(
        self,
        *,
        message_text: str,
        criteria: SearchCriteria,
        conversation_state: ConversationState | None,
    ) -> SearchCriteria:
        """Interpret a short answer only through the active backend question.

        Outside an active question, `position` and `axle` remain independent.
        When the backend explicitly asked for the axle, however, its governed
        options are "Dianteiro" and "Traseiro". A direct answer using one of
        those options must fill `axle`, rather than loop forever as `position`.
        """

        if not conversation_state or conversation_state.last_decision != "ask":
            return criteria

        pending_slot = str(conversation_state.pending_slot or "").strip()
        values = criteria.model_dump(exclude_none=False)

        if (
            pending_slot == "vehicle_year"
            and self._is_year_only_follow_up_answer(message_text)
        ):
            # "2008" may also be a catalog alias for Peugeot 2008. In an
            # answer to a pending year question it is year evidence, not a
            # vehicle-model correction.
            values["vehicle_model"] = None

        if (
            pending_slot == "axle"
            and values.get("axle") is None
            and values.get("position") is not None
            and self._is_direction_only_follow_up_answer(message_text)
        ):
            values["axle"] = values["position"]
            values["position"] = None

        if pending_slot == "engine":
            # Tokens such as EA111 can resemble a commercial code in an
            # isolated message. Under an active engine question, the governed
            # slot gives the token its unambiguous meaning.
            values["part_code"] = None
            engine = self._match_pending_engine_option(
                message_text=message_text,
                vehicle_model=(
                    values.get("vehicle_model")
                    or conversation_state.criteria.vehicle_model
                ),
                vehicle_year=(
                    values.get("vehicle_year")
                    or conversation_state.criteria.vehicle_year
                ),
            )
            if engine is not None:
                values["engine"] = engine

        return SearchCriteria.model_validate(values)

    def _match_pending_engine_option(
        self,
        *,
        message_text: str,
        vehicle_model: str | None,
        vehicle_year: int | None,
    ) -> str | None:
        """Return the catalog spelling of a textual engine option.

        Engine names are domain values (``BE``, ``Zetec Rocam``, ``EA211``),
        so parsing only a numeric displacement loses evidence supplied by the
        customer.  Match whole normalized options, prefer the longest form
        (``Duratec HE`` before ``Duratec``), and reject an option outside a
        known interval for the informed year.
        """
        model_key = normalize_pre_search_text(vehicle_model)
        normalized_message = normalize_pre_search_text(message_text)
        if not model_key or not normalized_message:
            return None

        details = self._engine_options_by_model.get(model_key, [])
        if not details:
            details = [
                (option, None, None)
                for option in self._engine_by_model.get(model_key, [])
            ]

        matches: list[tuple[str, int | None, int | None]] = []
        for option, year_from, year_to in details:
            normalized_option = normalize_pre_search_text(option)
            if not normalized_option or normalized_option == "nao sei":
                continue
            if re.search(rf"\b{re.escape(normalized_option)}\b", normalized_message):
                matches.append((option, year_from, year_to))
        if not matches:
            return None

        # The same option can have multiple ranges. It is valid if any range
        # covers the vehicle year; unknown ranges do not invalidate evidence.
        candidates_by_option: dict[str, list[tuple[int | None, int | None]]] = {}
        for option, year_from, year_to in matches:
            candidates_by_option.setdefault(option, []).append((year_from, year_to))
        for option in sorted(candidates_by_option, key=lambda value: len(value), reverse=True):
            intervals = candidates_by_option[option]
            if vehicle_year is None or any(
                (start is None or vehicle_year >= start)
                and (end is None or vehicle_year <= end)
                for start, end in intervals
            ):
                return option
        return None

    def _apply_pending_follow_up_answer_to_context(
        self,
        *,
        criteria: SearchCriteria,
        current_criteria: SearchCriteria,
        conversation_state: ConversationState | None,
        message_text: str,
    ) -> SearchCriteria:
        """Prevent contextual extraction from undoing a direct follow-up answer."""

        if not conversation_state or conversation_state.last_decision != "ask":
            return criteria

        pending_slot = str(conversation_state.pending_slot or "").strip()
        values = criteria.model_dump(exclude_none=False)

        # A multi-item follow-up belongs to the item selected by the backend,
        # not to the first family recovered from the preceding user message.
        # Start from that active item's criteria and then let the new message
        # replace only the values it explicitly contains.
        if (
            conversation_state.active_item_index is not None
            and pending_slot in SearchCriteria.model_fields
        ):
            active_values = conversation_state.criteria.model_dump(exclude_none=False)
            current_values = current_criteria.model_dump(exclude_none=False)
            for field_name, current_value in current_values.items():
                if current_value not in (None, "", []):
                    active_values[field_name] = current_value
            values = active_values

        if (
            pending_slot == "vehicle_year"
            and self._is_year_only_follow_up_answer(message_text)
        ):
            values["vehicle_year"] = current_criteria.vehicle_year
            values["vehicle_model"] = None

        if (
            pending_slot == "axle"
            and current_criteria.axle is not None
            and self._is_direction_only_follow_up_answer(message_text)
        ):
            values["axle"] = current_criteria.axle
            values["position"] = None

        if (
            pending_slot in SearchCriteria.model_fields
            and getattr(current_criteria, pending_slot, None) not in (None, "", [])
        ):
            values[pending_slot] = getattr(current_criteria, pending_slot)

        return SearchCriteria.model_validate(values)

    def _deterministic_identity_is_trusted(
        self,
        *,
        message_text: str,
        criteria: SearchCriteria,
        conversation_state: ConversationState | None,
        is_follow_up: bool,
    ) -> bool:
        if criteria.part_code:
            return True

        part_query = self._canonicalize_part_query(criteria.part_query)
        if not part_query or part_query in self._generic_ambiguous_parts:
            return False

        if self._dictionary_extractor.has_exact_part_query_match(
            message_text=message_text,
            canonical_part_query=part_query,
        ):
            return True

        if not is_follow_up or conversation_state is None:
            return False
        state_part_query = self._canonicalize_part_query(
            conversation_state.criteria.part_query
        )
        return state_part_query == part_query

    def _request_safety_confirmation(
        self,
        *,
        message_text: str,
        criteria: SearchCriteria,
    ) -> PreSearchValidation | None:
        """Stop before a search when a negative or vehicle identity is unclear."""
        intent = self._dictionary_extractor.resolve_request_intent(message_text)
        if intent.unresolved_reason:
            return PreSearchValidation(
                decision="ask",
                criteria=criteria,
                missing_fields=["intent_resolution"],
                next_question=NextQuestion(
                    key="intent_resolution",
                    prompt=(
                        "Entendi uma negacao ou correcao. Qual peca e qual aplicacao "
                        "devo considerar para pesquisar?"
                    ),
                ),
                confidence=0.99,
            )

        expected_brands = self._expected_brands_for_model(criteria.vehicle_model)
        actual_brand = normalize_pre_search_text(criteria.vehicle_brand)
        if actual_brand and expected_brands and actual_brand not in expected_brands:
            model = str(criteria.vehicle_model or "").strip()
            return PreSearchValidation(
                decision="ask",
                criteria=criteria,
                missing_fields=["vehicle_identity"],
                next_question=NextQuestion(
                    key="vehicle_identity",
                    prompt=(
                        f'Encontrei a marca "{criteria.vehicle_brand}" e o modelo "{model}", '
                        "que parecem conflitantes. Qual veiculo devo considerar?"
                    ),
                ),
                confidence=0.99,
            )
        return None

    def _expected_brands_for_model(self, model: str | None) -> set[str]:
        normalized_model = normalize_pre_search_text(model)
        if not normalized_model:
            return set()
        catalog_brands = self._model_brands.get(normalized_model, set())
        if catalog_brands:
            return set(catalog_brands)
        return set(MODEL_BRAND_FALLBACKS.get(normalized_model, set()))

    def _set_deterministic_safety_audit(self, result: PreSearchValidation) -> None:
        self._last_audit_info.set({
            "llm_endpoint_used": None,
            "llm_raw_content": None,
            "llm_output_valid": None,
            "llm_parse_error": None,
            "llm_fallback_used": None,
            "llm_decision_raw": None,
            "pre_search_path": "deterministic_ask",
            "deterministic_reason": result.missing_fields[0],
            "missing_fields": list(result.missing_fields),
            "next_question_key": (
                result.next_question.key if result.next_question is not None else None
            ),
        })

    def warmup(self) -> dict[str, Any]:
        payload = self._build_warmup_payload()
        started_at = time.perf_counter()
        response = httpx.post(
            f"{self._base_url}/api/generate",
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        raw_body = response.json()
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        summary = {
            "elapsed_ms": elapsed_ms,
            "load_duration_ms": self._duration_ns_to_ms(raw_body.get("load_duration")),
            "total_duration_ms": self._duration_ns_to_ms(raw_body.get("total_duration")),
            "keep_alive": payload.get("keep_alive"),
            "done": raw_body.get("done"),
        }
        self._logger.info(
            "pre_search_llm_warmup_completed",
            extra={
                "model": self._model,
                **summary,
            },
        )
        return summary

    def validate(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
        conversation_state: ConversationState | None = None,
    ) -> PreSearchValidation:
        self._last_audit_info.set(None)
        context = last_messages or []
        # Values explicitly found in the current message are authoritative.
        # The contextual extraction is still used for omitted fields, but it
        # must not allow an old vehicle/part or an LLM guess to overwrite a
        # correction made by the user now.
        current_message_criteria = self._normalize_pending_follow_up_current_criteria(
            message_text=message_text,
            criteria=self._dictionary_extractor.extract(
                message_text,
                last_messages=[],
            ),
            conversation_state=conversation_state,
        )
        safety_result = self._request_safety_confirmation(
            message_text=message_text,
            criteria=current_message_criteria,
        )
        if safety_result is not None:
            self._set_deterministic_safety_audit(safety_result)
            return safety_result
        dictionary_criteria = self._dictionary_extractor.extract(
            message_text,
            last_messages=context,
        )
        dictionary_criteria = self._apply_pending_follow_up_answer_to_context(
            criteria=dictionary_criteria,
            current_criteria=current_message_criteria,
            conversation_state=conversation_state,
            message_text=message_text,
        )
        merged_seed_criteria = self._merge_dictionary_with_conversation_state(
            dictionary_criteria=dictionary_criteria,
            conversation_state=conversation_state,
        )
        payload = self._build_chat_payload(
            message_text=message_text,
            last_messages=context,
            dictionary_seed_criteria=merged_seed_criteria,
            conversation_state=conversation_state,
        )

        llm_started_at = time.perf_counter()
        try:
            raw_body, endpoint_used = self._post_chat_or_generate(
                payload=payload,
                message_text=message_text,
                last_messages=context,
                dictionary_seed_criteria=merged_seed_criteria,
                conversation_state=conversation_state,
            )
            if self._log_raw_response:
                self._log_raw_ollama_response(
                    endpoint_used=endpoint_used,
                    message_text=message_text,
                    last_messages=context,
                    dictionary_seed_criteria=merged_seed_criteria,
                    raw_body=raw_body,
                )
        except Exception as exc:
            self._logger.exception(
                "pre_search_llm_unavailable",
                extra={
                    "model": self._model,
                    "base_url": self._base_url,
                },
            )
            raise PreSearchServiceUnavailableError(
                "Validador de pesquisa indisponivel no momento."
            ) from exc

        llm_elapsed_ms = round((time.perf_counter() - llm_started_at) * 1000, 2)
        audit_info = self._last_audit_info.get() or {}
        audit_info["llm_elapsed_ms"] = llm_elapsed_ms
        self._last_audit_info.set(audit_info)

        content = ""
        try:
            content = self._extract_content(raw_body)
            parsed = self._parse_content(content)
            coerced = self._coerce_validation_payload(parsed)
            llm_validation = PreSearchValidation.model_validate(coerced)
            self._set_last_audit_info(
                endpoint_used=endpoint_used,
                raw_content=content,
                output_valid=True,
                parse_error=None,
                fallback_used=False,
            )
        except Exception as exc:
            self._set_last_audit_info(
                endpoint_used=endpoint_used,
                raw_content=content,
                output_valid=False,
                parse_error=str(exc),
                fallback_used=True,
            )
            ai_fallback = self._build_ai_decision_fallback(
                raw_content=content,
                dictionary_criteria=merged_seed_criteria,
                message_text=message_text,
                last_messages=context,
            )
            self._logger.warning(
                "pre_search_llm_invalid_output_fallback_ai_raw",
                extra={
                    "model": self._model,
                    "base_url": self._base_url,
                    "fallback_decision": ai_fallback.decision,
                    "fallback_criteria": ai_fallback.criteria.model_dump(exclude_none=True),
                },
            )
            if self._log_raw_response:
                self._logger.info(
                    "pre_search_llm_fallback_from_raw_text",
                    extra={
                        "model": self._model,
                        "decision": ai_fallback.decision,
                        "criteria": ai_fallback.criteria.model_dump(exclude_none=True),
                        "missing_fields": ai_fallback.missing_fields,
                        "next_question": (
                            ai_fallback.next_question.model_dump(exclude_none=True)
                            if ai_fallback.next_question
                            else None
                        ),
                        "parse_error": str(exc),
                    },
                )
            audit_info = self._last_audit_info.get() or {}
            audit_info["llm_elapsed_ms"] = llm_elapsed_ms
            self._last_audit_info.set(audit_info)
            return ai_fallback

        audit_info = self._last_audit_info.get() or {}
        audit_info["llm_elapsed_ms"] = llm_elapsed_ms
        self._last_audit_info.set(audit_info)

        llm_validation = self._merge_validation_with_dictionary_seed(
            llm_validation=llm_validation,
            dictionary_criteria=merged_seed_criteria,
            message_text=message_text,
            last_messages=context,
            conversation_state=conversation_state,
            current_message_criteria=current_message_criteria,
        )
        if self._log_raw_response:
            score_explicit_fields = self._build_score_explicit_fields(
                dictionary_criteria=merged_seed_criteria,
            )
            criteria_score = self._calculate_criteria_score(
                llm_validation.criteria,
                score_explicit_fields=score_explicit_fields,
            )
            self._logger.info(
                "pre_search_llm_final_validation",
                extra={
                    "model": self._model,
                    "decision": llm_validation.decision,
                    "criteria": llm_validation.criteria.model_dump(exclude_none=True),
                    "missing_fields": llm_validation.missing_fields,
                    "criteria_score": criteria_score,
                    "score_explicit_fields": sorted(score_explicit_fields),
                    "min_score_to_search": self._min_score_to_search,
                    "conversation_state": (
                        conversation_state.model_dump(exclude_none=True)
                        if conversation_state
                        else None
                    ),
                    "next_question": (
                        llm_validation.next_question.model_dump(exclude_none=True)
                        if llm_validation.next_question
                        else None
                    ),
                },
            )
        return llm_validation

    def _set_last_audit_info(
        self,
        *,
        endpoint_used: str | None,
        raw_content: str | None,
        output_valid: bool,
        parse_error: str | None,
        fallback_used: bool,
    ) -> None:
        content = str(raw_content or "").strip() or None
        self._last_audit_info.set({
            "llm_endpoint_used": endpoint_used,
            "llm_raw_content": content,
            "llm_output_valid": bool(output_valid),
            "llm_parse_error": parse_error,
            "llm_fallback_used": bool(fallback_used),
            "llm_decision_raw": self._extract_decision_from_raw_content(content or ""),
        })

    def _post_chat_or_generate(
        self,
        *,
        payload: dict[str, Any],
        message_text: str,
        last_messages: list[dict[str, Any]],
        dictionary_seed_criteria: SearchCriteria,
        conversation_state: ConversationState | None,
    ) -> tuple[dict[str, Any], str]:
        chat_endpoint = f"{self._base_url}/api/chat"
        response = httpx.post(chat_endpoint, json=payload, timeout=self._timeout)
        endpoint_used = "/api/chat"

        if response.status_code == 404:
            generate_payload = self._build_generate_payload(
                message_text=message_text,
                last_messages=last_messages,
                dictionary_seed_criteria=dictionary_seed_criteria,
                conversation_state=conversation_state,
            )
            generate_endpoint = f"{self._base_url}/api/generate"
            response = httpx.post(generate_endpoint, json=generate_payload, timeout=self._timeout)
            endpoint_used = "/api/generate"

        response.raise_for_status()
        return response.json(), endpoint_used

    def _build_chat_payload(
        self,
        *,
        message_text: str,
        last_messages: list[dict[str, Any]],
        dictionary_seed_criteria: SearchCriteria,
        conversation_state: ConversationState | None,
    ) -> dict[str, Any]:
        instructions = self._build_system_instructions(categories_text=self._categories_text)
        score_policy = self._build_llm_score_policy(dictionary_seed_criteria=dictionary_seed_criteria)
        user_input = self._build_residual_llm_input(
            message_text=message_text,
            last_messages=last_messages,
            dictionary_seed_criteria=dictionary_seed_criteria,
            conversation_state=conversation_state,
            score_policy=score_policy,
        )
        return {
            "model": self._model,
            "stream": False,
            "think": self._think,
            "format": self._response_schema(),
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(user_input, ensure_ascii=False)},
            ],
            "options": {
                "temperature": self._temperature,
                "num_predict": self._num_predict,
            },
            **({"keep_alive": self._keep_alive} if self._keep_alive else {}),
        }

    def _build_generate_payload(
        self,
        *,
        message_text: str,
        last_messages: list[dict[str, Any]],
        dictionary_seed_criteria: SearchCriteria,
        conversation_state: ConversationState | None,
    ) -> dict[str, Any]:
        instructions = self._build_system_instructions(categories_text=self._categories_text)
        score_policy = self._build_llm_score_policy(dictionary_seed_criteria=dictionary_seed_criteria)
        user_input = self._build_residual_llm_input(
            message_text=message_text,
            last_messages=last_messages,
            dictionary_seed_criteria=dictionary_seed_criteria,
            conversation_state=conversation_state,
            score_policy=score_policy,
        )
        prompt = (
            f"{instructions}\n\n"
            "Entrada JSON:\n"
            f"{json.dumps(user_input, ensure_ascii=False)}\n\n"
            "Saida JSON:"
        )
        return {
            "model": self._model,
            "stream": False,
            "think": self._think,
            "format": self._response_schema(),
            "prompt": prompt,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._num_predict,
            },
            **({"keep_alive": self._keep_alive} if self._keep_alive else {}),
        }

    def _build_warmup_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 1,
            },
        }
        if self._keep_alive:
            payload["keep_alive"] = self._keep_alive
        return payload

    @staticmethod
    def _build_residual_llm_input(
        *,
        message_text: str,
        last_messages: list[dict[str, Any]],
        dictionary_seed_criteria: SearchCriteria,
        conversation_state: ConversationState | None,
        score_policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Make evidence source and precedence machine-readable to the LLM."""
        previous_user_messages = [
            message
            for message in last_messages
            if str(message.get("role", "")).strip().lower() == "user"
        ]
        assistant_context = [
            message
            for message in last_messages
            if str(message.get("role", "")).strip().lower() == "assistant"
        ]
        return {
            "residual_only": True,
            "evidence_precedence": [
                "current_user_message",
                "current_message_dictionary_seed",
                "active_conversation_state_for_omitted_fields",
                "previous_user_messages_for_omitted_fields",
                "assistant_messages_context_only",
            ],
            "message_text": message_text,
            "previous_user_messages": previous_user_messages,
            "assistant_context": assistant_context,
            "dictionary_seed_criteria": dictionary_seed_criteria.model_dump(exclude_none=True),
            "conversation_state": conversation_state.model_dump(exclude_none=True) if conversation_state else None,
            "multi_item_rule": "A mensagem pode conter uma ou mais pecas; preserve cada peca em items quando houver mais de uma.",
            "score_policy": score_policy,
        }

    @staticmethod
    def _extract_content(raw_body: dict[str, Any]) -> str:
        if not isinstance(raw_body, dict):
            raise ValueError("Resposta da LLM em formato inesperado.")

        message = raw_body.get("message")
        if isinstance(message, dict):
            content = str(message.get("content", "")).strip()
            if content:
                return content
            thinking = str(message.get("thinking", "")).strip()
            if thinking:
                return thinking

        response_text = str(raw_body.get("response", "")).strip()
        if response_text:
            return response_text

        raise ValueError("Resposta vazia da LLM.")

    def _log_raw_ollama_response(
        self,
        *,
        endpoint_used: str,
        message_text: str,
        last_messages: list[dict[str, Any]],
        dictionary_seed_criteria: SearchCriteria,
        raw_body: dict[str, Any],
    ) -> None:
        preview = self._safe_preview(raw_body)
        self._logger.info(
            "pre_search_llm_raw_response",
            extra={
                "model": self._model,
                "endpoint_used": endpoint_used,
                "message_text": self._truncate_for_log(message_text, 400),
                "last_messages": [
                    {
                        "role": str(message.get("role", "")),
                        "text": self._truncate_for_log(str(message.get("text", "")), 240),
                    }
                    for message in last_messages
                ],
                "dictionary_seed_criteria": dictionary_seed_criteria.model_dump(exclude_none=True),
                "ollama_raw_preview": preview,
            },
        )

    def _safe_preview(self, raw_body: dict[str, Any]) -> str:
        try:
            content = self._extract_content(raw_body)
            if content:
                return self._truncate_for_log(content, 1200)
        except Exception:
            pass
        serialized = json.dumps(raw_body, ensure_ascii=True)
        return self._truncate_for_log(serialized, 1200)

    @staticmethod
    def _truncate_for_log(value: str, max_len: int) -> str:
        if len(value) <= max_len:
            return value
        return f"{value[:max_len]}...[truncated]"

    def _merge_dictionary_with_conversation_state(
        self,
        *,
        dictionary_criteria: SearchCriteria,
        conversation_state: ConversationState | None,
    ) -> SearchCriteria:
        if not conversation_state or not conversation_state.pending_slot:
            return self._canonicalize_criteria_part_query(dictionary_criteria)

        state_values = conversation_state.criteria.model_dump(exclude_none=False)
        merged_values = dictionary_criteria.model_dump(exclude_none=False)

        for key, state_value in state_values.items():
            if key == "part_code":
                continue
            current_value = merged_values.get(key)
            if current_value is None or current_value == "" or current_value == []:
                merged_values[key] = state_value

        merged_criteria = SearchCriteria.model_validate(merged_values)
        return self._canonicalize_criteria_part_query(merged_criteria)

    def _merge_validation_with_dictionary_seed(
        self,
        *,
        llm_validation: PreSearchValidation,
        dictionary_criteria: SearchCriteria,
        message_text: str,
        last_messages: list[dict[str, Any]],
        conversation_state: ConversationState | None,
        current_message_criteria: SearchCriteria | None = None,
    ) -> PreSearchValidation:
        explicit_part_code = bool(dictionary_criteria.part_code)
        merged_criteria = llm_validation.criteria.model_dump(exclude_none=False)
        dictionary_values = dictionary_criteria.model_dump(exclude_none=False)

        for key, dictionary_value in dictionary_values.items():
            llm_value = merged_criteria.get(key)
            if self._should_take_dictionary_value(llm_value=llm_value, dictionary_value=dictionary_value):
                merged_criteria[key] = dictionary_value

        if (
            conversation_state is not None
            and conversation_state.active_item_index is not None
            and str(conversation_state.pending_slot or "") in SearchCriteria.model_fields
        ):
            # The active item is selected by the backend.  Do not let an LLM
            # replay a previous item from chat history over that identity.
            for key, dictionary_value in dictionary_values.items():
                if key != "part_code":
                    merged_criteria[key] = dictionary_value

        # Current-message evidence wins over both the LLM and values recovered
        # from previous turns. This is what makes "Sprinter -> Hilux" and
        # user corrections behave as replacements instead of additions.
        if current_message_criteria is not None:
            current_values = current_message_criteria.model_dump(exclude_none=False)
            for key, current_value in current_values.items():
                if current_value not in (None, "", []):
                    merged_criteria[key] = current_value

        merged_criteria["part_query"] = self._canonicalize_part_query(
            merged_criteria.get("part_query"),
            fallback=dictionary_criteria.part_query,
        )
        merged_criteria["part_code"] = dictionary_criteria.part_code

        criteria_model = SearchCriteria.model_validate(merged_criteria)
        deterministic_items = self._dictionary_extractor.extract_items(message_text)
        if len(deterministic_items) > 1:
            # The LLM may still be useful for conversational wording, but it
            # cannot merge vehicle evidence across clauses.  The deterministic
            # extractor owns the item boundaries and the primary item is the
            # first explicit clause for the legacy top-level contract.
            deterministic_items = [
                self._canonicalize_criteria_part_query(item)
                for item in deterministic_items
            ]
            criteria_model = deterministic_items[0]
        score_explicit_fields = self._build_score_explicit_fields(
            dictionary_criteria=dictionary_criteria,
        )
        decision = llm_validation.decision
        missing_fields = self._resolve_missing_fields(
            criteria=criteria_model,
            llm_missing_fields=llm_validation.missing_fields,
            include_rule_fields=True,
            explicit_part_code=explicit_part_code,
        )
        criteria_score = self._calculate_criteria_score(
            criteria_model,
            score_explicit_fields=score_explicit_fields,
        )
        search_gate_missing = self._calculate_missing_fields(
            criteria_model,
            explicit_part_code=explicit_part_code,
        )
        if explicit_part_code and criteria_model.part_code:
            decision = "search"
            missing_fields = []
        elif decision == "search":
            if search_gate_missing:
                decision = "ask"
                missing_fields = self._resolve_missing_fields(
                    criteria=criteria_model,
                    llm_missing_fields=search_gate_missing,
                    include_rule_fields=True,
                    explicit_part_code=explicit_part_code,
                )
            elif (
                self._score_threshold_applies(
                    criteria_model,
                    explicit_part_code=explicit_part_code,
                )
                and criteria_score < self._min_score_to_search_for(criteria_model)
            ):
                decision = "ask"
                missing_fields = self._resolve_missing_fields(
                    criteria=criteria_model,
                    llm_missing_fields=self._calculate_score_gap_missing_fields(
                        criteria=criteria_model,
                        current_missing_fields=missing_fields,
                        score_explicit_fields=score_explicit_fields,
                        explicit_part_code=explicit_part_code,
                    ),
                    include_rule_fields=True,
                    explicit_part_code=explicit_part_code,
                )
        elif decision == "ask":
            # Mandatory fields, rules and score are backend-owned.  Once they
            # are complete, an optional field invented by the LLM must not
            # block a catalog search.  This covers both a regular complete
            # request and a corrected result-disambiguation follow-up.
            is_complete_for_search = (
                not search_gate_missing
                and (
                    not self._score_threshold_applies(
                        criteria_model,
                        explicit_part_code=explicit_part_code,
                    )
                    or criteria_score >= self._min_score_to_search_for(criteria_model)
                )
            )
            if is_complete_for_search:
                decision = "search"
                missing_fields = []

        if decision == "ask" and not missing_fields:
            missing_fields = self._resolve_missing_fields(
                criteria=criteria_model,
                llm_missing_fields=self._infer_ask_missing_fields(criteria_model),
                include_rule_fields=True,
                explicit_part_code=explicit_part_code,
            )

        if decision == "ask" and self._should_handoff_non_catalog_part(
            criteria=criteria_model,
            missing_fields=missing_fields,
            message_text=message_text,
            last_messages=last_messages,
        ):
            return self._build_non_catalog_part_handoff(
                criteria=criteria_model,
                confidence=llm_validation.confidence,
            )

        next_question: NextQuestion | None = None
        if decision == "ask":
            llm_next_question = llm_validation.next_question
            next_question = self._resolve_next_question(
                llm_next_question=llm_next_question,
                criteria=criteria_model,
                decision=decision,
                missing_fields=missing_fields,
            )
            if not next_question:
                next_question = self._build_default_next_question(
                    criteria=criteria_model,
                    missing_fields=missing_fields,
                )
            if next_question and next_question.key not in missing_fields:
                missing_fields = [next_question.key, *missing_fields]
            if not next_question:
                return self._build_no_decision_handoff(
                    criteria=criteria_model,
                    missing_fields=missing_fields,
                    confidence=llm_validation.confidence,
                )
        elif decision == "handoff":
            next_question = llm_validation.next_question

        return PreSearchValidation(
            decision=decision,
            criteria=criteria_model,
            items=deterministic_items or llm_validation.items,
            missing_fields=missing_fields,
            next_question=next_question,
            confidence=llm_validation.confidence,
        )

    def _should_promote_follow_up_ask_to_search(
        self,
        *,
        conversation_state: ConversationState | None,
        criteria: SearchCriteria,
        search_gate_missing: list[str],
        criteria_score: int,
        explicit_part_code: bool = False,
    ) -> bool:
        if not conversation_state or not conversation_state.pending_slot:
            return False
        if conversation_state.last_decision and conversation_state.last_decision != "ask":
            return False

        pending_slot = str(conversation_state.pending_slot or "").strip()
        if pending_slot not in SearchCriteria.model_fields:
            return False
        if search_gate_missing:
            return False
        if (
            self._score_threshold_applies(criteria, explicit_part_code=explicit_part_code)
            and criteria_score < self._min_score_to_search_for(criteria)
        ):
            return False
        return True

    def _should_take_dictionary_value(self, *, llm_value: Any, dictionary_value: Any) -> bool:
        if dictionary_value is None or dictionary_value == "" or dictionary_value == []:
            return False
        if llm_value is None or llm_value == "" or llm_value == []:
            return True
        if isinstance(llm_value, str) and self._is_invalid_slot_text(llm_value):
            return True
        return False

    def _resolve_missing_fields(
        self,
        *,
        criteria: SearchCriteria,
        llm_missing_fields: list[str],
        include_rule_fields: bool = True,
        explicit_part_code: bool = False,
    ) -> list[str]:
        rules_missing_fields = (
            self._calculate_missing_fields(criteria, explicit_part_code=explicit_part_code)
            if include_rule_fields
            else []
        )
        ordered_fields = [*rules_missing_fields, *llm_missing_fields]
        deduped_fields: list[str] = []
        criteria_values = criteria.model_dump(exclude_none=False)

        for field in ordered_fields:
            field_name = str(field).strip()
            if not field_name or field_name in deduped_fields:
                continue
            if not self._is_follow_up_field_allowed(criteria=criteria, field_name=field_name):
                continue
            if field_name == "axle" and criteria_values.get("axle") is not None:
                continue
            current_value = criteria_values.get(field_name)
            if current_value is None or current_value == "" or current_value == []:
                deduped_fields.append(field_name)

        return deduped_fields

    def _resolve_decision(
        self,
        *,
        llm_decision: str,
        criteria: SearchCriteria,
        missing_fields: list[str],
    ) -> str:
        _ = criteria
        _ = missing_fields
        return llm_decision

    def _resolve_next_question(
        self,
        *,
        llm_next_question: NextQuestion | None,
        criteria: SearchCriteria,
        decision: str,
        missing_fields: list[str],
    ) -> NextQuestion | None:
        if decision == "handoff":
            return llm_next_question

        if decision != "ask":
            return None

        if not llm_next_question:
            return None

        next_key = str(llm_next_question.key).strip()
        if not next_key:
            return None

        criteria_values = criteria.model_dump(exclude_none=False)
        next_value = criteria_values.get(next_key)
        if next_value is not None and next_value != "" and next_value != []:
            return None

        if missing_fields and next_key not in missing_fields:
            if not self._is_follow_up_field_allowed(criteria=criteria, field_name=next_key):
                return None

        if next_key in {"side", "position", "axle"}:
            return self._build_default_next_question(
                criteria=criteria,
                missing_fields=[next_key],
            )

        return llm_next_question

    def _build_ai_decision_fallback(
        self,
        *,
        raw_content: str,
        dictionary_criteria: SearchCriteria,
        message_text: str,
        last_messages: list[dict[str, Any]],
    ) -> PreSearchValidation:
        explicit_part_code = bool(dictionary_criteria.part_code)
        ai_decision = self._extract_decision_from_raw_content(raw_content)
        score_explicit_fields = self._build_score_explicit_fields(
            dictionary_criteria=dictionary_criteria,
        )
        missing_fields = self._resolve_missing_fields(
            criteria=dictionary_criteria,
            llm_missing_fields=[],
            include_rule_fields=True,
            explicit_part_code=explicit_part_code,
        )
        criteria_score = self._calculate_criteria_score(
            dictionary_criteria,
            score_explicit_fields=score_explicit_fields,
        )
        search_gate_missing = self._calculate_missing_fields(
            dictionary_criteria,
            explicit_part_code=explicit_part_code,
        )
        if explicit_part_code and dictionary_criteria.part_code:
            ai_decision = "search"
            missing_fields = []
        elif ai_decision == "search":
            if search_gate_missing:
                ai_decision = "ask"
                missing_fields = self._resolve_missing_fields(
                    criteria=dictionary_criteria,
                    llm_missing_fields=search_gate_missing,
                    include_rule_fields=True,
                    explicit_part_code=explicit_part_code,
                )
            elif (
                self._score_threshold_applies(
                    dictionary_criteria,
                    explicit_part_code=explicit_part_code,
                )
                and criteria_score < self._min_score_to_search_for(dictionary_criteria)
            ):
                ai_decision = "ask"
                missing_fields = self._resolve_missing_fields(
                    criteria=dictionary_criteria,
                    llm_missing_fields=self._calculate_score_gap_missing_fields(
                        criteria=dictionary_criteria,
                        current_missing_fields=missing_fields,
                        score_explicit_fields=score_explicit_fields,
                        explicit_part_code=explicit_part_code,
                    ),
                    include_rule_fields=True,
                    explicit_part_code=explicit_part_code,
                )

        decision = self._resolve_decision(
            llm_decision=ai_decision,
            criteria=dictionary_criteria,
            missing_fields=missing_fields,
        )

        if decision == "ask" and self._should_handoff_non_catalog_part(
            criteria=dictionary_criteria,
            missing_fields=missing_fields,
            message_text=message_text,
            last_messages=last_messages,
        ):
            return self._build_non_catalog_part_handoff(
                criteria=dictionary_criteria,
                confidence=0.6,
            )

        next_question: NextQuestion | None = None
        if decision == "ask":
            next_question = self._resolve_next_question(
                llm_next_question=None,
                criteria=dictionary_criteria,
                decision=decision,
                missing_fields=missing_fields,
            )
            if not next_question:
                next_question = self._build_default_next_question(
                    criteria=dictionary_criteria,
                    missing_fields=missing_fields,
                )

        if decision == "ask" and not next_question:
            return self._build_no_decision_handoff(
                criteria=dictionary_criteria,
                missing_fields=missing_fields,
                confidence=0.2,
            )

        if decision == "ask" and next_question and next_question.key not in missing_fields:
            missing_fields = [next_question.key, *missing_fields]

        return PreSearchValidation(
            decision=decision,
            criteria=dictionary_criteria,
            missing_fields=missing_fields,
            next_question=next_question if decision == "ask" else None,
            confidence=0.6,
        )

    def _build_default_next_question(
        self,
        *,
        criteria: SearchCriteria,
        missing_fields: list[str],
    ) -> NextQuestion | None:
        ordered_missing = [str(field or "").strip() for field in missing_fields if str(field or "").strip()]
        if not ordered_missing:
            return None

        field_name = ordered_missing[0]
        prompts: dict[str, str] = {
            "part_query": "Qual peca voce precisa?",
            "part_code": "Qual o codigo da peca?",
            "vehicle_brand": "Qual a marca do veiculo?",
            "vehicle_model": "Qual o modelo do veiculo?",
            "vehicle_year": "Qual o ano do veiculo?",
            "engine": "Qual a motorizacao do veiculo?",
            "side": "Esquerdo ou direito?",
            "position": "Dianteiro ou traseiro?",
            "axle": "Eixo dianteiro ou traseiro?",
            "variant": "Qual a versao do veiculo?",
            "quantity": "Quantas unidades voce precisa?",
        }
        prompt = prompts.get(field_name)
        if field_name == "variant" and criteria.part_query == "lubrificantes":
            prompt = "Qual a especificacao do oleo (por exemplo, 20W50)?"
        if not prompt:
            return None

        options: list[str] | None = None
        if field_name == "engine":
            options = self._engine_options_for_model(criteria.vehicle_model)
        elif field_name == "side":
            options = ["Esquerdo", "Direito", "Nao sei"]
        elif field_name in {"position", "axle"}:
            options = ["Dianteiro", "Traseiro", "Nao sei"]

        return NextQuestion(
            key=field_name,
            prompt=prompt,
            options=options,
        )

    @staticmethod
    def _build_no_decision_handoff(
        *,
        criteria: SearchCriteria,
        missing_fields: list[str],
        confidence: float,
    ) -> PreSearchValidation:
        return PreSearchValidation(
            decision="handoff",
            criteria=criteria,
            missing_fields=missing_fields,
            next_question=NextQuestion(
                key="handoff",
                prompt=(
                    "Nao tenho capacidade de decisao automatica para esta solicitacao. "
                    "Vou encaminhar para atendimento humano."
                ),
                options=None,
            ),
            confidence=max(0.0, min(confidence, 0.3)),
        )

    @staticmethod
    def _build_non_catalog_part_handoff(
        *,
        criteria: SearchCriteria,
        confidence: float,
    ) -> PreSearchValidation:
        return PreSearchValidation(
            decision="handoff",
            criteria=criteria,
            missing_fields=[],
            next_question=NextQuestion(
                key="handoff",
                prompt=UNSUPPORTED_PART_HANDOFF_PROMPT,
                options=None,
            ),
            confidence=max(0.0, min(confidence, 0.6)),
        )

    def _should_handoff_non_catalog_part(
        self,
        *,
        criteria: SearchCriteria,
        missing_fields: list[str],
        message_text: str,
        last_messages: list[dict[str, Any]],
    ) -> bool:
        if criteria.part_query or criteria.part_code:
            return False
        if "part_query" not in missing_fields:
            return False
        if not (criteria.vehicle_model or criteria.vehicle_year or criteria.vehicle_brand):
            return False
        return bool(
            self._non_catalog_part_candidate_tokens(
                criteria=criteria,
                message_text=message_text,
                last_messages=last_messages,
            )
        )

    def _non_catalog_part_candidate_tokens(
        self,
        *,
        criteria: SearchCriteria,
        message_text: str,
        last_messages: list[dict[str, Any]],
    ) -> list[str]:
        texts = [message_text]
        texts.extend(
            str(message.get("text", ""))
            for message in last_messages
            if str(message.get("role", "")).strip().lower() in {"", "user"}
        )
        normalized_text = normalize_pre_search_text(" ".join(texts))
        tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", normalized_text)
            if token and not token.isdigit()
        ]
        ignored_tokens = self._non_catalog_part_ignored_tokens(criteria)
        return [
            token
            for token in tokens
            if len(token) >= 3
            and token not in ignored_tokens
            and not self._is_invalid_slot_text(token)
        ]

    def _non_catalog_part_ignored_tokens(self, criteria: SearchCriteria) -> set[str]:
        ignored = set(UNSUPPORTED_PART_STOPWORDS)
        if criteria.vehicle_brand:
            ignored.update(normalize_pre_search_text(criteria.vehicle_brand).split())
        if criteria.preferred_product_brand:
            ignored.update(
                normalize_pre_search_text(criteria.preferred_product_brand).split()
            )
        if criteria.vehicle_model:
            ignored.update(normalize_pre_search_text(criteria.vehicle_model).split())
        if criteria.vehicle_year:
            ignored.add(str(criteria.vehicle_year))
        if criteria.engine:
            ignored.update(re.findall(r"[a-z0-9]+", normalize_pre_search_text(criteria.engine)))
        ignored.update(self._known_group_terms)
        ignored.update({"left", "right", "front", "rear"})
        ignored.update({"esq", "dir", "esquerdo", "direito", "dianteiro", "traseiro"})
        return {token for token in ignored if token}

    @staticmethod
    def _extract_decision_from_raw_content(raw_content: str) -> str:
        lowered = (raw_content or "").lower()
        if re.search(r'"decision"\s*:\s*"handoff"', lowered):
            return "handoff"
        if re.search(r'"decision"\s*:\s*"ask"', lowered):
            return "ask"
        if re.search(r'"decision"\s*:\s*"search"', lowered):
            return "search"
        return "ask"

    def _calculate_missing_fields(
        self,
        criteria: SearchCriteria,
        *,
        explicit_part_code: bool = False,
    ) -> list[str]:
        missing: list[str] = []
        part_query = str(criteria.part_query or "").strip().lower() or None
        has_explicit_part_code = bool(criteria.part_code and explicit_part_code)

        if not part_query and not has_explicit_part_code:
            missing.append("part_query")
            return missing

        if has_explicit_part_code:
            return missing

        if not criteria.vehicle_model and part_query not in VEHICLE_OPTIONAL_PART_QUERIES:
            missing.append("vehicle_model")
            return missing

        if self._requires_vehicle_year_for_minimum_search_identity(criteria):
            missing.append("vehicle_year")

        if not criteria.vehicle_year and part_query in self._generic_ambiguous_parts:
            if "vehicle_year" not in missing:
                missing.append("vehicle_year")

        if part_query in self._needs_engine and not criteria.engine:
            missing.append("engine")

        if part_query in self._needs_side and not criteria.side:
            missing.append("side")

        if part_query in self._needs_position and not criteria.position:
            missing.append("position")

        if part_query in self._needs_axle and not criteria.axle:
            missing.append("axle")

        if part_query in self._needs_variant and not criteria.variant:
            missing.append("variant")

        return missing

    @staticmethod
    def _normalize_criteria_weights(raw_weights: dict[str, int] | None) -> dict[str, int]:
        normalized_weights = dict(DEFAULT_CRITERIA_WEIGHTS)
        if not raw_weights:
            return normalized_weights

        for raw_key, raw_weight in raw_weights.items():
            key = str(raw_key or "").strip().lower()
            if key not in normalized_weights:
                continue
            try:
                parsed_weight = int(raw_weight)
            except (TypeError, ValueError):
                continue
            normalized_weights[key] = max(parsed_weight, 0)

        return normalized_weights

    def _score_threshold_applies(
        self,
        criteria: SearchCriteria,
        *,
        explicit_part_code: bool = False,
    ) -> bool:
        if criteria.part_code and explicit_part_code:
            return False
        return self._min_score_to_search_for(criteria) > 0

    def _calculate_criteria_score(
        self,
        criteria: SearchCriteria,
        *,
        score_explicit_fields: set[str] | None = None,
    ) -> int:
        score = 0
        for field_name, weight in self._criteria_weights.items():
            if weight <= 0:
                continue
            if self._is_field_excluded_from_score(
                field_name=field_name,
                score_explicit_fields=score_explicit_fields,
            ):
                continue
            if self._is_criteria_field_filled(criteria, field_name):
                score += weight
        return score

    @staticmethod
    def _requires_vehicle_year_for_minimum_search_identity(criteria: SearchCriteria) -> bool:
        if not criteria.part_query or not criteria.vehicle_model:
            return False
        if criteria.vehicle_year:
            return False
        if criteria.part_code:
            return False
        if criteria.engine or criteria.side or criteria.position or criteria.axle or criteria.variant:
            return False
        if criteria.quantity is not None:
            return False
        return True

    def _calculate_score_gap_missing_fields(
        self,
        *,
        criteria: SearchCriteria,
        current_missing_fields: list[str],
        score_explicit_fields: set[str] | None = None,
        explicit_part_code: bool = False,
    ) -> list[str]:
        if not self._score_threshold_applies(criteria, explicit_part_code=explicit_part_code):
            return current_missing_fields

        remaining_score = self._min_score_to_search_for(criteria) - self._calculate_criteria_score(
            criteria,
            score_explicit_fields=score_explicit_fields,
        )
        if remaining_score <= 0:
            return current_missing_fields

        selected_fields: list[str] = []

        for field_name in current_missing_fields:
            normalized_name = str(field_name or "").strip()
            if not normalized_name or normalized_name in selected_fields:
                continue
            if self._is_criteria_field_filled(criteria, normalized_name):
                continue
            if self._is_field_excluded_from_score(
                field_name=normalized_name,
                score_explicit_fields=score_explicit_fields,
            ):
                continue
            selected_fields.append(normalized_name)
            remaining_score -= max(self._criteria_weights.get(normalized_name, 0), 0)
            if remaining_score <= 0:
                return selected_fields

        for field_name in self._sorted_weighted_fields_for_ask(criteria):
            if field_name in selected_fields:
                continue
            if self._is_criteria_field_filled(criteria, field_name):
                continue
            if self._is_field_excluded_from_score(
                field_name=field_name,
                score_explicit_fields=score_explicit_fields,
            ):
                continue
            selected_fields.append(field_name)
            remaining_score -= max(self._criteria_weights.get(field_name, 0), 0)
            if remaining_score <= 0:
                break

        if selected_fields:
            return selected_fields
        if not criteria.part_query and not criteria.part_code:
            return ["part_query"]
        if not criteria.vehicle_model:
            return ["vehicle_model"]
        return ["vehicle_year"]

    def _infer_ask_missing_fields(self, criteria: SearchCriteria) -> list[str]:
        for field_name in self._sorted_weighted_fields_for_ask(criteria):
            if self._is_criteria_field_filled(criteria, field_name):
                continue
            if not self._is_follow_up_field_allowed(criteria=criteria, field_name=field_name):
                continue
            return [field_name]

        if not criteria.part_query and not criteria.part_code:
            return ["part_query"]
        if not criteria.vehicle_model:
            return ["vehicle_model"]
        if criteria.part_query and not criteria.vehicle_year:
            return ["vehicle_year"]
        return []

    def _build_llm_score_policy(self, *, dictionary_seed_criteria: SearchCriteria) -> dict[str, Any]:
        explicit_part_code = bool(dictionary_seed_criteria.part_code) 
        effective_min_score = self._min_score_to_search_for(dictionary_seed_criteria)
        score_explicit_fields = self._build_score_explicit_fields(
            dictionary_criteria=dictionary_seed_criteria,
        )
        seed_score = self._calculate_criteria_score(
            dictionary_seed_criteria,
            score_explicit_fields=score_explicit_fields,
        )
        seed_missing_fields = self._calculate_missing_fields(
            dictionary_seed_criteria,
            explicit_part_code=explicit_part_code,
        )
        score_gap_missing_fields_hint = self._calculate_score_gap_missing_fields(
            criteria=dictionary_seed_criteria,
            current_missing_fields=seed_missing_fields,
            score_explicit_fields=score_explicit_fields,
            explicit_part_code=explicit_part_code,
        )
        seed_expected_decision_by_policy = self._seed_expected_decision_by_policy(
            criteria=dictionary_seed_criteria,
            seed_score=seed_score,
            seed_missing_fields=seed_missing_fields,
            explicit_part_code=explicit_part_code,
        )
        return {
            "criteria_weights": dict(self._criteria_weights),
            "min_score_to_search": effective_min_score,
            "min_score_to_search_global": self._min_score_to_search,
            "seed_score": seed_score,
            "seed_missing_fields": seed_missing_fields,
            "score_gap_missing_fields_hint": score_gap_missing_fields_hint,
            "score_explicit_fields": sorted(score_explicit_fields),
            "score_only_if_explicit": ["vehicle_brand"],
            "seed_expected_decision_by_policy": seed_expected_decision_by_policy,
            "part_code_bypass": explicit_part_code,
        }

    def _seed_expected_decision_by_policy(
        self,
        *,
        criteria: SearchCriteria,
        seed_score: int,
        seed_missing_fields: list[str],
        explicit_part_code: bool = False,
    ) -> str:
        if criteria.part_code and explicit_part_code:
            return "search_or_ask"
        if seed_missing_fields:
            return "ask"
        if (
            self._score_threshold_applies(
                criteria,
                explicit_part_code=explicit_part_code,
            )
            and seed_score < self._min_score_to_search_for(criteria)
        ):
            return "ask"
        return "search_or_ask"

    @staticmethod
    def _normalize_part_min_score_overrides(raw_overrides: dict[str, int] | None) -> dict[str, int]:
        normalized: dict[str, int] = {}
        if not raw_overrides:
            return normalized

        for raw_part_name, raw_score in raw_overrides.items():
            part_name = str(raw_part_name or "").strip().lower()
            if not part_name:
                continue
            try:
                parsed_score = int(raw_score)
            except (TypeError, ValueError):
                continue
            normalized[part_name] = max(parsed_score, 0)
        return normalized

    def _min_score_to_search_for(self, criteria: SearchCriteria) -> int:
        part_query = str(criteria.part_query or "").strip().lower()
        if part_query and part_query in self._min_score_to_search_by_part:
            return self._min_score_to_search_by_part[part_query]
        return self._min_score_to_search

    @staticmethod
    def _build_score_explicit_fields(*, dictionary_criteria: SearchCriteria) -> set[str]:
        explicit_fields: set[str] = set()
        if dictionary_criteria.vehicle_brand:
            explicit_fields.add("vehicle_brand")
        return explicit_fields

    @staticmethod
    def _is_field_excluded_from_score(
        *,
        field_name: str,
        score_explicit_fields: set[str] | None,
    ) -> bool:
        normalized_field = str(field_name or "").strip().lower()
        if normalized_field != "vehicle_brand":
            return False
        if score_explicit_fields is None:
            return False
        return "vehicle_brand" not in score_explicit_fields

    def _sorted_weighted_fields_for_ask(self, criteria: SearchCriteria) -> list[str]:
        weighted_fields: list[tuple[str, int]] = []
        for field_name, weight in self._criteria_weights.items():
            if weight <= 0:
                continue
            if not self._is_scoring_field_relevant(criteria, field_name):
                continue
            weighted_fields.append((field_name, weight))

        weighted_fields.sort(
            key=lambda item: (
                -item[1],
                self._field_priority(item[0]),
            )
        )
        return [field_name for field_name, _ in weighted_fields]

    def _is_scoring_field_relevant(self, criteria: SearchCriteria, field_name: str) -> bool:
        normalized_name = str(field_name or "").strip().lower()
        part_query = str(criteria.part_query or "").strip().lower() or None

        if normalized_name == "part_code":
            return not bool(criteria.part_query)
        if normalized_name == "quantity":
            return False
        if normalized_name == "side":
            return part_query in self._needs_side
        if normalized_name == "position":
            return part_query in self._needs_position
        if normalized_name == "axle":
            return part_query in self._needs_axle and not criteria.axle
        if normalized_name == "variant":
            return part_query in self._needs_variant
        if normalized_name == "engine":
            return bool(criteria.vehicle_model) or (part_query in self._needs_engine)
        return True

    def _is_follow_up_field_allowed(self, *, criteria: SearchCriteria, field_name: str) -> bool:
        normalized_name = str(field_name or "").strip().lower()
        if not normalized_name:
            return False
        if normalized_name == "part_code":
            return not bool(criteria.part_query)
        if normalized_name == "vehicle_brand":
            return not bool(criteria.vehicle_model)
        if normalized_name == "quantity":
            return False
        return self._is_scoring_field_relevant(criteria, normalized_name)

    @staticmethod
    def _field_priority(field_name: str) -> int:
        try:
            return SCORING_FIELD_PRIORITY.index(field_name)
        except ValueError:
            return len(SCORING_FIELD_PRIORITY)

    @staticmethod
    def _is_criteria_field_filled(criteria: SearchCriteria, field_name: str) -> bool:
        if not hasattr(criteria, field_name):
            return False
        value = getattr(criteria, field_name)
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True

    @staticmethod
    def _parse_content(content: str) -> dict[str, Any]:
        if not content:
            raise ValueError("Resposta vazia da LLM.")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            return json.loads(content[start : end + 1])

    @staticmethod
    def _response_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["decision", "criteria", "missing_fields", "next_question", "confidence"],
            "properties": {
                "decision": {"type": "string", "enum": ["search", "ask", "handoff"]},
                "criteria": {
                    "type": "object",
                    "properties": {
                        "part_query": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "part_code": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "preferred_product_brand": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "vehicle_brand": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "vehicle_model": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "vehicle_year": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                        "engine": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "side": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "position": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "axle": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "variant": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "quantity": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                    },
                    "additionalProperties": False,
                },
                "items": {
                    "type": "array",
                    "description": "Uma ou mais pecas independentes; use um objeto por peca.",
                    "items": {"type": "object", "additionalProperties": True},
                },
                "missing_fields": {"type": "array", "items": {"type": "string"}},
                "next_question": {
                    "anyOf": [
                        {"type": "null"},
                        {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "key": {"type": "string"},
                                "prompt": {"type": "string"},
                                "options": {
                                    "anyOf": [
                                        {"type": "array", "items": {"type": "string"}},
                                        {"type": "null"},
                                    ]
                                },
                            },
                            "required": ["type", "key", "prompt"],
                            "additionalProperties": False,
                        },
                    ]
                },
                "confidence": {"type": "number"},
                "criteria_score": {"anyOf": [{"type": "number"}, {"type": "null"}]},
            },
            "additionalProperties": False,
        }

    def _coerce_validation_payload(self, parsed: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(parsed, dict):
            raise ValueError("JSON da LLM em formato invalido.")

        criteria_raw = parsed.get("criteria")
        criteria = criteria_raw if isinstance(criteria_raw, dict) else {}

        part_query = self._canonicalize_part_query(self._as_str(criteria.get("part_query")))
        preferred_product_brand = self._clean_preferred_product_brand(
            self._as_str(criteria.get("preferred_product_brand"))
        )
        vehicle_brand = self._clean_vehicle_brand(self._as_str(criteria.get("vehicle_brand")))
        vehicle_model = self._clean_vehicle_model(self._as_str(criteria.get("vehicle_model")))
        vehicle_year = self._parse_year(criteria.get("vehicle_year"))
        part_code = None
        engine = self._as_str(criteria.get("engine"))
        side = self._normalize_side(self._as_str(criteria.get("side")))
        position = self._normalize_position(self._as_str(criteria.get("position")))
        axle = self._normalize_axle(self._as_str(criteria.get("axle")))
        variant = self._as_str(criteria.get("variant"))
        quantity = self._parse_quantity(criteria.get("quantity"))

        normalized_criteria: dict[str, Any] = {
            "part_query": part_query,
            "part_code": part_code,
            "preferred_product_brand": preferred_product_brand,
            "vehicle_brand": vehicle_brand,
            "vehicle_model": vehicle_model,
            "vehicle_year": vehicle_year,
            "engine": engine,
            "side": side,
            "position": position,
            "axle": axle,
            "variant": variant,
            "quantity": quantity,
        }

        decision = self._normalize_decision(parsed.get("decision"), normalized_criteria)
        missing_fields = self._normalize_missing_fields(parsed.get("missing_fields"))
        confidence = self._normalize_confidence(parsed.get("confidence"))
        next_question = self._normalize_next_question(parsed.get("next_question"))
        normalized_items: list[SearchCriteria] | None = None
        if isinstance(parsed.get("items"), list):
            normalized_items = []
            for raw_item in parsed["items"]:
                if isinstance(raw_item, dict):
                    try:
                        normalized_items.append(SearchCriteria.model_validate(raw_item))
                    except Exception:
                        continue
            if not normalized_items:
                normalized_items = None

        return {
            "decision": decision,
            "criteria": normalized_criteria,
            "items": normalized_items,
            "missing_fields": missing_fields,
            "next_question": next_question,
            "confidence": confidence,
        }

    @staticmethod
    def _normalize_decision(value: Any, criteria: dict[str, Any]) -> str:
        decision = str(value or "").strip().lower()
        if decision in {"search", "ask", "handoff"}:
            return decision
        if criteria.get("part_query") or criteria.get("part_code"):
            return "search"
        return "ask"

    def _canonicalize_part_query(self, value: Any, *, fallback: str | None = None) -> str | None:
        text = self._as_str(value)
        if text:
            canonical = self._dictionary_extractor.canonicalize_part_query(text)
            if canonical:
                return canonical
        if fallback:
            canonical_fallback = self._dictionary_extractor.canonicalize_part_query(fallback)
            if canonical_fallback:
                return canonical_fallback
        return None

    def _canonicalize_criteria_part_query(self, criteria: SearchCriteria) -> SearchCriteria:
        canonical_part_query = self._canonicalize_part_query(criteria.part_query)
        if canonical_part_query == criteria.part_query:
            return criteria

        values = criteria.model_dump(exclude_none=False)
        values["part_query"] = canonical_part_query
        return SearchCriteria.model_validate(values)

    @staticmethod
    def _normalize_missing_fields(value: Any) -> list[str]:
        known_fields = {
            "part_query",
            "part_code",
            "preferred_product_brand",
            "vehicle_brand",
            "vehicle_model",
            "vehicle_year",
            "engine",
            "side",
            "position",
            "axle",
            "variant",
            "quantity",
        }
        if not isinstance(value, list):
            return []
        result: list[str] = []
        for raw_item in value:
            item = str(raw_item or "").strip().lower()
            if item in known_fields and item not in result:
                result.append(item)
        return result

    @staticmethod
    def _normalize_next_question(value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None

        key = str(value.get("key", "")).strip()
        prompt = str(value.get("prompt", "")).strip()
        if not key or not prompt:
            return None

        options: list[str] | None = None
        raw_options = value.get("options")
        if isinstance(raw_options, list):
            options = [str(item).strip() for item in raw_options if str(item).strip()]
            if not options:
                options = None

        return {
            "type": "request_info",
            "key": key,
            "prompt": prompt,
            "options": options,
        }

    @staticmethod
    def _normalize_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.5
        if confidence > 1 and confidence <= 100:
            confidence = confidence / 100
        if confidence < 0:
            return 0.0
        if confidence > 1:
            return 1.0
        return confidence

    def _as_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered in self._invalid_slot_tokens:
            return None
        return text

    def _is_invalid_slot_text(self, value: str) -> bool:
        normalized = str(value or "").strip().lower()
        return normalized in self._invalid_slot_tokens

    @staticmethod
    def _parse_year(value: Any) -> int | None:
        if value is None:
            return None
        year_text = str(value).strip()
        match = re.search(r"\b(19\d{2}|20\d{2})\b", year_text)
        if not match:
            return None
        year = int(match.group(1))
        if 1900 <= year <= 2100:
            return year
        return None

    @staticmethod
    def _parse_quantity(value: Any) -> int | None:
        if value is None:
            return None
        try:
            quantity = int(value)
        except (TypeError, ValueError):
            return None
        if 1 <= quantity <= 999:
            return quantity
        return None

    @staticmethod
    def _clean_preferred_product_brand(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"\s+", " ", value).strip()
        known_brands = {"ngk": "NGK", "nakata": "Nakata", "cofap": "Cofap"}
        return known_brands.get(cleaned.casefold(), cleaned.title()) or None

    @staticmethod
    def _clean_vehicle_model(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"\b(19\d{2}|20\d{2})\b", "", value).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned:
            return None
        if cleaned.lower() == "s10":
            return "S10"
        return cleaned.title()

    @staticmethod
    def _clean_vehicle_brand(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            return None
        return cleaned.title()

    @staticmethod
    def _normalize_side(value: str | None) -> str | None:
        if not value:
            return None
        lowered = value.lower()
        if lowered in {"left", "esq", "esquerdo", "esquerda"}:
            return "left"
        if lowered in {"right", "dir", "direito", "direita"}:
            return "right"
        return None

    @staticmethod
    def _normalize_position(value: str | None) -> str | None:
        if not value:
            return None
        lowered = value.lower()
        if lowered in {"front", "dianteiro", "dianteira", "diant"}:
            return "front"
        if lowered in {"rear", "traseiro", "traseira", "tras"}:
            return "rear"
        return None

    @staticmethod
    def _normalize_axle(value: str | None) -> str | None:
        if not value:
            return None
        lowered = value.lower()
        if lowered in {"front", "dianteiro", "dianteira", "eixo dianteiro", "eixo dianteira"}:
            return "front"
        if lowered in {"rear", "traseiro", "traseira", "eixo traseiro", "eixo traseira"}:
            return "rear"
        return None

    def _looks_like_part_code(
        self,
        value: str,
        *,
        vehicle_brand: str | None = None,
        vehicle_model: str | None = None,
        vehicle_year: int | None = None,
    ) -> bool:
        return is_valid_part_code_candidate(
            value,
            compiled_patterns=self._part_code_patterns,
            vehicle_brand=vehicle_brand,
            vehicle_model=vehicle_model,
            vehicle_year=vehicle_year,
        )

    def _engine_options_for_model(self, model_name: str | None) -> list[str]:
        key = str(model_name or "").strip().lower()
        return self._engine_by_model.get(key, ["1.0", "1.6", "2.0", "Nao sei"])

    @staticmethod
    def _build_system_instructions(*, categories_text: str | None = None) -> str:
        base = (
            "Voce valida pre-busca de autopecas e retorna somente JSON. "
            "Campos obrigatorios no JSON final: decision, criteria, missing_fields, next_question, confidence. "
            "decision deve ser: search, ask ou handoff. "
            "criteria usa apenas: part_query, part_code, preferred_product_brand, vehicle_brand, vehicle_model, vehicle_year, engine, side, position, axle, variant, quantity. "
            "preferred_product_brand e a marca comercial desejada da peca, como NGK, Nakata ou Cofap; nao confunda com vehicle_brand. Ela e preferencia de ranking, nunca filtro obrigatorio: outras marcas compativeis continuam validas. "
            "Uma mensagem pode pedir uma ou varias pecas. Para duas ou mais familias independentes, preencha tambem items como uma lista de criteria, um objeto por peca, preservando quantity e os filtros especificos; nunca descarte as pecas extras. "
            "part_query deve ser uma familia canonica do catalogo; nao use plural, sinonimo ou typo quando existir forma canonica. "
            "Se nao conseguir mapear a peca para uma familia canonica do catalogo, retorne part_query como null. "
            "Regras: sem part_query e sem part_code -> ask; "
            "com part_code valido -> search; "
            "para termos ambiguos como filtro/correia/pastilha sem modelo ou ano -> ask; "
            "pecas dependentes de lado/posicao/eixo/versao podem ser search com missing_fields e next_question. "
            "Este e o caminho residual: ele so e chamado quando o backend nao resolveu a solicitacao deterministicamente. "
            "Siga evidence_precedence estritamente: mensagem atual vence; o seed da mensagem atual confirma campos catalogados; ConversationState so completa campo omitido do item ativo; mensagens anteriores do usuario so completam omissoes; mensagens do assistant sao contexto, nunca evidencia factual. "
            "Nunca reutilize valor historico que conflite com a mensagem atual. "
            "Use dictionary_seed_criteria como extracao deterministica de alta confianca para preencher slots. "
            "Se houver conflito fraco, prefira dictionary_seed_criteria. "
            "So preencha part_code quando ele aparecer literalmente em message_text, last_messages ou dictionary_seed_criteria.part_code. "
            "Nao invente part_code combinando modelo com ano, como GOL-2010, ONIX-2018 ou similares. "
            "Use score_policy para decidir search vs ask na PRIMEIRA resposta: "
            "calcule criteria_score somando os pesos de score_policy.criteria_weights para cada campo preenchido em criteria; "
            "para vehicle_brand, so pontue quando constar em score_policy.score_explicit_fields; "
            "se score_policy.part_code_bypass for true e houver part_code valido, pode search mesmo com score baixo; "
            "sem part_code, se criteria_score < score_policy.min_score_to_search, decision DEVE ser ask; "
            "score_policy.seed_expected_decision_by_policy e um limite minimo de decisao para esta entrada: "
            "se vier 'ask', sua decision nao pode ser search; use ask ou handoff. "
            "neste caso, missing_fields deve priorizar score_policy.score_gap_missing_fields_hint. "
            "Se decision=ask, next_question deve vir preenchido no MESMO JSON (nao pode ser null). "
            "next_question.key deve ser um campo de missing_fields e next_question.prompt deve ser direto e especifico. Para side use esquerdo/direito; para position use dianteiro/traseiro; axle so existe quando a familia o exigir. "
            "Quando nao souber um slot, retorne null. "
            "Nao use strings como 'nao', 'desconhecido' ou similares em criteria."
        )
        if not categories_text:
            return base
        return f"{base} Catalogo de categorias/subgrupos (use como referencia sem copiar texto literal): {categories_text}"

    @staticmethod
    def _load_categories_text(path: str | None) -> str | None:
        if not path:
            return None
        category_file = Path(path)
        if not category_file.exists():
            return None
        content = category_file.read_text(encoding="utf-8").strip()
        if not content:
            return None
        return content[:4000]

    @staticmethod
    def _normalize_keep_alive(value: str | None) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @staticmethod
    def _duration_ns_to_ms(value: Any) -> float | None:
        try:
            return round(float(value) / 1_000_000, 2)
        except (TypeError, ValueError):
            return None
