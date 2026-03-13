import json
import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.errors import PreSearchServiceUnavailableError
from app.core.domain.pre_search import NextQuestion, PreSearchValidation, SearchCriteria
from app.core.ports.pre_search_validator import PreSearchValidatorPort
from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor
from app.infra.pre_search_part_code import (
    compile_part_code_patterns,
    is_valid_part_code_candidate,
)

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
        self._think = settings.llm_think
        self._log_raw_response = settings.llm_log_raw_response
        self._categories_text = self._load_categories_text(settings.llm_categories_file)
        self._invalid_slot_tokens = set(catalog.invalid_slot_tokens)
        self._generic_ambiguous_parts = set(catalog.generic_ambiguous_parts)
        self._needs_side = set(catalog.needs_side)
        self._needs_position = set(catalog.needs_position)
        self._needs_axle = set(catalog.needs_axle)
        self._needs_engine = set(catalog.needs_engine)
        self._needs_variant = set(catalog.needs_variant)
        self._engine_by_model = {
            str(model).lower(): list(options)
            for model, options in catalog.engine_by_model.items()
        }
        self._part_code_patterns = compile_part_code_patterns(catalog.part_code_patterns)
        self._criteria_weights = self._normalize_criteria_weights(catalog.criteria_weights)
        self._min_score_to_search = max(int(catalog.min_score_to_search), 0)
        self._dictionary_extractor = DictionaryPreSearchExtractor(catalog=catalog)
        self._last_audit_info: dict[str, Any] | None = None

    def get_last_audit(self) -> dict[str, Any] | None:
        if self._last_audit_info is None:
            return None
        return deepcopy(self._last_audit_info)

    def validate(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
    ) -> PreSearchValidation:
        self._last_audit_info = None
        context = last_messages or []
        dictionary_criteria = self._dictionary_extractor.extract(
            message_text,
            last_messages=context,
        )
        payload = self._build_chat_payload(
            message_text=message_text,
            last_messages=context,
            dictionary_seed_criteria=dictionary_criteria,
        )

        try:
            raw_body, endpoint_used = self._post_chat_or_generate(
                payload=payload,
                message_text=message_text,
                last_messages=context,
                dictionary_seed_criteria=dictionary_criteria,
            )
            if self._log_raw_response:
                self._log_raw_ollama_response(
                    endpoint_used=endpoint_used,
                    message_text=message_text,
                    last_messages=context,
                    dictionary_seed_criteria=dictionary_criteria,
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
                dictionary_criteria=dictionary_criteria,
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
            return ai_fallback

        llm_validation = self._merge_validation_with_dictionary_seed(
            llm_validation=llm_validation,
            dictionary_criteria=dictionary_criteria,
            message_text=message_text,
            last_messages=context,
        )
        if self._log_raw_response:
            score_explicit_fields = self._build_score_explicit_fields(
                dictionary_criteria=dictionary_criteria,
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
        self._last_audit_info = {
            "llm_endpoint_used": endpoint_used,
            "llm_raw_content": content,
            "llm_output_valid": bool(output_valid),
            "llm_parse_error": parse_error,
            "llm_fallback_used": bool(fallback_used),
            "llm_decision_raw": self._extract_decision_from_raw_content(content or ""),
        }

    def _post_chat_or_generate(
        self,
        *,
        payload: dict[str, Any],
        message_text: str,
        last_messages: list[dict[str, Any]],
        dictionary_seed_criteria: SearchCriteria,
    ) -> tuple[dict[str, Any], str]:
        chat_endpoint = f"{self._base_url}/api/chat"
        response = httpx.post(chat_endpoint, json=payload, timeout=self._timeout)
        endpoint_used = "/api/chat"

        if response.status_code == 404:
            generate_payload = self._build_generate_payload(
                message_text=message_text,
                last_messages=last_messages,
                dictionary_seed_criteria=dictionary_seed_criteria,
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
    ) -> dict[str, Any]:
        instructions = self._build_system_instructions(categories_text=self._categories_text)
        score_policy = self._build_llm_score_policy(dictionary_seed_criteria=dictionary_seed_criteria)
        user_input = {
            "message_text": message_text,
            "last_messages": last_messages,
            "dictionary_seed_criteria": dictionary_seed_criteria.model_dump(exclude_none=True),
            "score_policy": score_policy,
        }
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
        }

    def _build_generate_payload(
        self,
        *,
        message_text: str,
        last_messages: list[dict[str, Any]],
        dictionary_seed_criteria: SearchCriteria,
    ) -> dict[str, Any]:
        instructions = self._build_system_instructions(categories_text=self._categories_text)
        score_policy = self._build_llm_score_policy(dictionary_seed_criteria=dictionary_seed_criteria)
        user_input = {
            "message_text": message_text,
            "last_messages": last_messages,
            "dictionary_seed_criteria": dictionary_seed_criteria.model_dump(exclude_none=True),
            "score_policy": score_policy,
        }
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

    def _merge_validation_with_dictionary_seed(
        self,
        *,
        llm_validation: PreSearchValidation,
        dictionary_criteria: SearchCriteria,
        message_text: str,
        last_messages: list[dict[str, Any]],
    ) -> PreSearchValidation:
        explicit_part_code = bool(dictionary_criteria.part_code)
        merged_criteria = llm_validation.criteria.model_dump(exclude_none=False)
        dictionary_values = dictionary_criteria.model_dump(exclude_none=False)

        for key, dictionary_value in dictionary_values.items():
            llm_value = merged_criteria.get(key)
            if self._should_take_dictionary_value(llm_value=llm_value, dictionary_value=dictionary_value):
                merged_criteria[key] = dictionary_value

        criteria_model = SearchCriteria.model_validate(merged_criteria)
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
                and criteria_score < self._min_score_to_search
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
            missing_fields=missing_fields,
            next_question=next_question,
            confidence=llm_validation.confidence,
        )

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
            if field_name == "axle" and (
                criteria_values.get("axle") is not None or criteria_values.get("position") is not None
            ):
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
            return None

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
                and criteria_score < self._min_score_to_search
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
            "side": "Qual lado da peca?",
            "position": "Em qual posicao a peca fica?",
            "axle": "Qual o eixo da peca?",
            "variant": "Qual a versao do veiculo?",
            "quantity": "Quantas unidades voce precisa?",
        }
        prompt = prompts.get(field_name)
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

        if not criteria.vehicle_model:
            missing.append("vehicle_model")
            return missing

        if not criteria.vehicle_year and part_query in self._generic_ambiguous_parts:
            missing.append("vehicle_year")

        if part_query in self._needs_engine and not criteria.engine:
            missing.append("engine")

        if part_query in self._needs_side and not criteria.side:
            missing.append("side")

        if part_query in self._needs_position and not criteria.position:
            missing.append("position")

        has_axle = criteria.axle or criteria.position
        if part_query in self._needs_axle and not has_axle:
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
        return self._min_score_to_search > 0

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

        remaining_score = self._min_score_to_search - self._calculate_criteria_score(
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

    def _build_llm_score_policy(self, *, dictionary_seed_criteria: SearchCriteria) -> dict[str, Any]:
        explicit_part_code = bool(dictionary_seed_criteria.part_code)
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
            "min_score_to_search": self._min_score_to_search,
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
            and seed_score < self._min_score_to_search
        ):
            return "ask"
        return "search_or_ask"

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
            return part_query in self._needs_axle and not criteria.position
        if normalized_name == "variant":
            return part_query in self._needs_variant
        if normalized_name == "engine":
            return bool(criteria.vehicle_model) or (part_query in self._needs_engine)
        return True

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

        part_query = self._as_str(criteria.get("part_query"))
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

        return {
            "decision": decision,
            "criteria": normalized_criteria,
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

    @staticmethod
    def _normalize_missing_fields(value: Any) -> list[str]:
        known_fields = {
            "part_query",
            "part_code",
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
            "criteria usa apenas: part_query, part_code, vehicle_brand, vehicle_model, vehicle_year, engine, side, position, axle, variant, quantity. "
            "Regras: sem part_query e sem part_code -> ask; "
            "com part_code valido -> search; "
            "para termos ambiguos como filtro/correia/pastilha sem modelo ou ano -> ask; "
            "pecas dependentes de lado/posicao/eixo/versao podem ser search com missing_fields e next_question. "
            "Use message_text e last_messages juntos no contexto. "
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
            "next_question.key deve ser um campo de missing_fields e next_question.prompt deve ser direto e especifico. "
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
