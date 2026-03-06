import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.core.domain.errors import PreSearchServiceUnavailableError
from app.core.domain.pre_search import NextQuestion, PreSearchValidation, SearchCriteria
from app.core.ports.pre_search_validator import PreSearchValidatorPort
from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor


class LLMPreSearchValidator(PreSearchValidatorPort):
    _invalid_slot_tokens = {
        "nao",
        "none",
        "n/a",
        "desconhecido",
        "na",
        "null",
        "indefinido",
        "-",
    }
    _generic_ambiguous_parts = {"filtro", "correia", "pastilha de freio"}
    _needs_side = {"bandeja", "farol", "retrovisor", "lanterna traseira", "sensor abs", "amortecedor"}
    _needs_position = {
        "pastilha de freio",
        "disco de freio",
        "rolamento roda",
        "amortecedor",
        "sensor abs",
        "parachoque",
    }
    _needs_engine = {
        "correia dentada",
        "kit correia",
        "correia",
        "bomba d'agua",
        "radiador",
        "vela ignicao",
        "motor arranque",
        "bico injetor",
        "embreagem",
        "kit embreagem",
    }
    _engine_by_model = {
        "ecosport": ["1.6", "2.0", "Nao sei"],
        "gol": ["1.0", "1.6", "Nao sei"],
        "fiesta": ["1.0", "1.6", "Nao sei"],
        "onix": ["1.0", "1.4", "Nao sei"],
        "civic": ["1.8", "2.0", "Nao sei"],
        "corolla": ["1.8", "2.0", "Nao sei"],
        "hilux": ["2.5", "3.0", "Nao sei"],
    }

    def __init__(self, *, settings: Settings, logger: logging.Logger) -> None:
        self._logger = logger
        self._base_url = settings.llm_base_url.rstrip("/")
        self._model = settings.llm_model
        self._timeout = max(settings.llm_timeout_ms, 1000) / 1000
        self._temperature = settings.llm_temperature
        self._num_predict = max(settings.llm_num_predict, 64)
        self._think = settings.llm_think
        self._log_raw_response = settings.llm_log_raw_response
        self._categories_text = self._load_categories_text(settings.llm_categories_file)
        self._dictionary_extractor = DictionaryPreSearchExtractor()

    def validate(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
    ) -> PreSearchValidation:
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
        except Exception as exc:
            ai_fallback = self._build_ai_decision_fallback(
                raw_content=content,
                dictionary_criteria=dictionary_criteria,
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
        )
        if self._log_raw_response:
            self._logger.info(
                "pre_search_llm_final_validation",
                extra={
                    "model": self._model,
                    "decision": llm_validation.decision,
                    "criteria": llm_validation.criteria.model_dump(exclude_none=True),
                    "missing_fields": llm_validation.missing_fields,
                    "next_question": (
                        llm_validation.next_question.model_dump(exclude_none=True)
                        if llm_validation.next_question
                        else None
                    ),
                },
            )
        return llm_validation

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
        user_input = {
            "message_text": message_text,
            "last_messages": last_messages,
            "dictionary_seed_criteria": dictionary_seed_criteria.model_dump(exclude_none=True),
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
        user_input = {
            "message_text": message_text,
            "last_messages": last_messages,
            "dictionary_seed_criteria": dictionary_seed_criteria.model_dump(exclude_none=True),
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
    ) -> PreSearchValidation:
        merged_criteria = llm_validation.criteria.model_dump(exclude_none=False)
        dictionary_values = dictionary_criteria.model_dump(exclude_none=False)

        for key, dictionary_value in dictionary_values.items():
            llm_value = merged_criteria.get(key)
            if self._should_take_dictionary_value(llm_value=llm_value, dictionary_value=dictionary_value):
                merged_criteria[key] = dictionary_value

        criteria_model = SearchCriteria.model_validate(merged_criteria)
        missing_fields = self._resolve_missing_fields(
            criteria=criteria_model,
            llm_missing_fields=llm_validation.missing_fields,
        )
        decision = self._resolve_decision(
            llm_decision=llm_validation.decision,
            criteria=criteria_model,
            missing_fields=missing_fields,
        )
        next_question = self._resolve_next_question(
            llm_next_question=llm_validation.next_question,
            criteria=criteria_model,
            decision=decision,
            missing_fields=missing_fields,
        )

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
    ) -> list[str]:
        rules_missing_fields = self._calculate_missing_fields(criteria)
        ordered_fields = [*rules_missing_fields, *llm_missing_fields]
        deduped_fields: list[str] = []
        criteria_values = criteria.model_dump(exclude_none=False)

        for field in ordered_fields:
            field_name = str(field).strip()
            if not field_name or field_name in deduped_fields:
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
        if llm_decision == "handoff":
            return "handoff"

        if criteria.part_code:
            return "search"

        if not criteria.part_query:
            return "ask"

        if "part_query" in missing_fields or "vehicle_model" in missing_fields:
            return "ask"

        if criteria.part_query in self._generic_ambiguous_parts and "vehicle_year" in missing_fields:
            return "ask"

        if llm_decision == "ask":
            return "ask"

        return "search"

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

        if not missing_fields:
            return None

        if llm_next_question:
            next_key = str(llm_next_question.key).strip()
            criteria_values = criteria.model_dump(exclude_none=False)
            next_value = criteria_values.get(next_key)
            if next_key in missing_fields and (next_value is None or next_value == "" or next_value == []):
                return llm_next_question

        return self._build_next_question(criteria, missing_fields)

    def _build_ai_decision_fallback(
        self,
        *,
        raw_content: str,
        dictionary_criteria: SearchCriteria,
    ) -> PreSearchValidation:
        ai_decision = self._extract_decision_from_raw_content(raw_content)
        missing_fields = self._calculate_missing_fields(dictionary_criteria)
        next_question = self._build_next_question(dictionary_criteria, missing_fields)
        decision = self._resolve_decision(
            llm_decision=ai_decision,
            criteria=dictionary_criteria,
            missing_fields=missing_fields,
        )

        if decision == "ask" and not missing_fields and not dictionary_criteria.part_code:
            missing_fields = ["part_query"]
            next_question = self._build_next_question(dictionary_criteria, missing_fields)

        return PreSearchValidation(
            decision=decision,
            criteria=dictionary_criteria,
            missing_fields=missing_fields,
            next_question=next_question if (decision != "handoff" and missing_fields) else None,
            confidence=0.6,
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

    def _calculate_missing_fields(self, criteria: SearchCriteria) -> list[str]:
        missing: list[str] = []

        if not criteria.part_query and not criteria.part_code:
            missing.append("part_query")
            return missing

        if criteria.part_code:
            return missing

        if not criteria.vehicle_model:
            missing.append("vehicle_model")
            return missing

        if not criteria.vehicle_year and criteria.part_query in self._generic_ambiguous_parts:
            missing.append("vehicle_year")

        if criteria.part_query in self._needs_engine and not criteria.engine:
            missing.append("engine")

        if criteria.part_query in self._needs_side and not criteria.side:
            missing.append("side")

        if criteria.part_query in self._needs_position and not criteria.position:
            missing.append("position")

        return missing

    def _build_next_question(self, criteria: SearchCriteria, missing_fields: list[str]) -> NextQuestion | None:
        if not missing_fields:
            return None

        question_key = self._pick_question_key(criteria, missing_fields)
        if not question_key:
            return None

        if question_key == "part_query":
            return NextQuestion(
                key="part_query",
                prompt="Qual peca voce precisa?",
                options=None,
            )

        if question_key == "vehicle_model":
            part_name = criteria.part_query or "peca"
            return NextQuestion(
                key="vehicle_model",
                prompt=f"Para qual veiculo e o {part_name}?",
                options=None,
            )

        if question_key == "vehicle_year":
            model_name = criteria.vehicle_model or "veiculo"
            return NextQuestion(
                key="vehicle_year",
                prompt=f"Qual o ano do {model_name}?",
                options=None,
            )

        if question_key == "engine":
            options = self._engine_by_model.get((criteria.vehicle_model or "").lower(), ["1.0", "1.6", "2.0", "Nao sei"])
            return NextQuestion(
                key="engine",
                prompt="Qual motorizacao?",
                options=options,
            )

        if question_key == "side":
            return NextQuestion(
                key="side",
                prompt="Lado esquerdo ou direito?",
                options=["esquerdo", "direito", "Nao sei"],
            )

        if question_key == "position":
            return NextQuestion(
                key="position",
                prompt="E dianteiro ou traseiro?",
                options=["dianteiro", "traseiro", "Nao sei"],
            )

        return None

    @staticmethod
    def _pick_question_key(criteria: SearchCriteria, missing_fields: list[str]) -> str | None:
        if "part_query" in missing_fields:
            return "part_query"
        if "vehicle_model" in missing_fields:
            return "vehicle_model"
        if "side" in missing_fields and criteria.part_query in {"retrovisor", "farol", "lanterna traseira", "bandeja"}:
            return "side"
        if "position" in missing_fields and criteria.part_query in {"disco de freio", "pastilha de freio", "parachoque"}:
            return "position"
        if "vehicle_year" in missing_fields:
            return "vehicle_year"
        if "engine" in missing_fields:
            return "engine"
        if "position" in missing_fields:
            return "position"
        if "side" in missing_fields:
            return "side"
        return None

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
                        "vehicle_model": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "vehicle_year": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                        "engine": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "side": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "position": {"anyOf": [{"type": "string"}, {"type": "null"}]},
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
            },
            "additionalProperties": False,
        }

    def _coerce_validation_payload(self, parsed: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(parsed, dict):
            raise ValueError("JSON da LLM em formato invalido.")

        criteria_raw = parsed.get("criteria")
        criteria = criteria_raw if isinstance(criteria_raw, dict) else {}

        part_code = self._as_str(criteria.get("part_code"))
        if part_code and not self._looks_like_part_code(part_code):
            part_code = None

        part_query = self._as_str(criteria.get("part_query"))
        vehicle_model = self._clean_vehicle_model(self._as_str(criteria.get("vehicle_model")))
        vehicle_year = self._parse_year(criteria.get("vehicle_year"))
        engine = self._as_str(criteria.get("engine"))
        side = self._normalize_side(self._as_str(criteria.get("side")))
        position = self._normalize_position(self._as_str(criteria.get("position")))
        quantity = self._parse_quantity(criteria.get("quantity"))

        normalized_criteria: dict[str, Any] = {
            "part_query": part_query,
            "part_code": part_code,
            "vehicle_model": vehicle_model,
            "vehicle_year": vehicle_year,
            "engine": engine,
            "side": side,
            "position": position,
            "quantity": quantity,
        }

        decision = self._normalize_decision(parsed.get("decision"), normalized_criteria)
        missing_fields = self._normalize_missing_fields(parsed.get("missing_fields"))
        confidence = self._normalize_confidence(parsed.get("confidence"))
        next_question = self._normalize_next_question(parsed.get("next_question"))

        if not normalized_criteria["part_query"] and not normalized_criteria["part_code"]:
            if "part_query" not in missing_fields:
                missing_fields.insert(0, "part_query")
            decision = "ask"

        if decision == "ask" and missing_fields and not next_question:
            next_question = self._default_next_question(
                key=missing_fields[0],
                criteria=normalized_criteria,
            )

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
            "vehicle_model",
            "vehicle_year",
            "engine",
            "side",
            "position",
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

    @staticmethod
    def _as_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered in LLMPreSearchValidator._invalid_slot_tokens:
            return None
        return text

    @staticmethod
    def _is_invalid_slot_text(value: str) -> bool:
        normalized = str(value or "").strip().lower()
        return normalized in LLMPreSearchValidator._invalid_slot_tokens

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
    def _looks_like_part_code(value: str) -> bool:
        return bool(re.search(r"\b[A-Za-z]{2,5}[- ]?\d{3,8}\b", value))

    @staticmethod
    def _default_next_question(*, key: str, criteria: dict[str, Any]) -> dict[str, Any] | None:
        if key == "part_query":
            return {
                "type": "request_info",
                "key": "part_query",
                "prompt": "Qual peca voce precisa?",
                "options": None,
            }
        if key == "vehicle_model":
            part_name = criteria.get("part_query") or "peca"
            return {
                "type": "request_info",
                "key": "vehicle_model",
                "prompt": f"Para qual veiculo e o {part_name}?",
                "options": None,
            }
        if key == "vehicle_year":
            model_name = criteria.get("vehicle_model") or "veiculo"
            return {
                "type": "request_info",
                "key": "vehicle_year",
                "prompt": f"Qual o ano do {model_name}?",
                "options": None,
            }
        if key == "engine":
            return {
                "type": "request_info",
                "key": "engine",
                "prompt": "Qual motorizacao?",
                "options": ["1.0", "1.6", "2.0", "Nao sei"],
            }
        if key == "side":
            return {
                "type": "request_info",
                "key": "side",
                "prompt": "Lado esquerdo ou direito?",
                "options": ["esquerdo", "direito", "Nao sei"],
            }
        if key == "position":
            return {
                "type": "request_info",
                "key": "position",
                "prompt": "E dianteiro ou traseiro?",
                "options": ["dianteiro", "traseiro", "Nao sei"],
            }
        return None

    @staticmethod
    def _build_system_instructions(*, categories_text: str | None = None) -> str:
        base = (
            "Voce valida pre-busca de autopecas e retorna somente JSON. "
            "Campos obrigatorios no JSON final: decision, criteria, missing_fields, next_question, confidence. "
            "decision deve ser: search, ask ou handoff. "
            "criteria usa apenas: part_query, part_code, vehicle_model, vehicle_year, engine, side, position, quantity. "
            "Regras: sem part_query e sem part_code -> ask; "
            "com part_code valido -> search; "
            "para termos ambiguos como filtro/correia/pastilha sem modelo ou ano -> ask; "
            "pecas dependentes de lado/posicao podem ser search com missing_fields e next_question. "
            "Use message_text e last_messages juntos no contexto. "
            "Use dictionary_seed_criteria como extracao deterministica de alta confianca para preencher slots. "
            "Se houver conflito fraco, prefira dictionary_seed_criteria. "
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
