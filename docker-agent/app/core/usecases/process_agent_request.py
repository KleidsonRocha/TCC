import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.api.schemas.contract_v1 import AgentRequestV1
from app.config import Settings
from app.core.domain.part_code import (
    has_literal_part_code_evidence,
    normalize_part_code_candidate,
)
from app.core.domain.models import ConversationState, HandoffInfo, ProcessResult, ToolTrace
from app.core.domain.pre_search import NextQuestion, PreSearchValidation, SearchCriteria
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.core.ports.pre_search_review_recorder import PreSearchReviewRecorderPort
from app.core.ports.pre_search_validator import PreSearchValidatorPort
from app.core.ports.tools import ToolsPort

UNSUPPORTED_PART_HANDOFF_PROMPT = (
    "Essa familia de peca nao esta no catalogo para pesquisa automatica. "
    "Vou encaminhar para atendimento humano."
)


class _StageTimer:
    def __init__(self) -> None:
        self._started_at = time.perf_counter()
        self._stage_latency_ms: dict[str, float] = {}

    @contextmanager
    def measure(self, stage_name: str) -> Iterator[None]:
        started_at = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            self._stage_latency_ms[stage_name] = (
                self._stage_latency_ms.get(stage_name, 0.0) + elapsed_ms
            )

    def build_tool_trace(
        self,
        *,
        used_tools: list[str],
        pre_search_path: str,
    ) -> ToolTrace:
        return ToolTrace(
            used_tools=list(used_tools),
            latency_ms=round((time.perf_counter() - self._started_at) * 1000, 2),
            stage_latency_ms={
                key: round(value, 2)
                for key, value in self._stage_latency_ms.items()
            },
            pre_search_path=pre_search_path,
        )


class ProcessAgentRequestUseCase:
    def __init__(
        self,
        *,
        tools: ToolsPort,
        pre_search_validator: PreSearchValidatorPort,
        settings: Settings,
        logger: logging.Logger,
        review_recorder: PreSearchReviewRecorderPort,
    ) -> None:
        self._tools = tools
        self._pre_search_validator = pre_search_validator
        self._settings = settings
        self._logger = logger
        self._review_recorder = review_recorder

    async def execute(self, payload: AgentRequestV1) -> ProcessResult:
        validate_schema_version(payload.schema_version)
        query = validate_message_text(payload.message.text)
        last_messages: list[dict[str, str]] = []
        incoming_state: ConversationState | None = None
        if payload.context:
            last_messages = [
                {"role": message.role, "text": message.text}
                for message in payload.context.last_messages
            ]
            incoming_state = payload.context.conversation_state

        timing = _StageTimer()
        with timing.measure("pre_search_validator"):
            pre_search, pre_search_path, used_tools = self._validate_pre_search(
                query=query,
                last_messages=last_messages,
                incoming_state=incoming_state,
            )
            pre_search = self._enforce_part_code_provenance(
                pre_search,
                message_text=query,
                last_messages=last_messages,
            )
            pre_search = self._canonicalize_validated_part_query(pre_search)

        with timing.measure("response_assembly"):
            current_state = self._build_conversation_state(
                criteria=pre_search.criteria,
                last_decision=pre_search.decision,
                next_question=pre_search.next_question,
            )
            actions: list[dict[str, object]] = []
            handoff = HandoffInfo(required=False, reason=None)
            confidence = 0.0
            if pre_search.decision == "ask" and pre_search.next_question:
                actions.append(pre_search.next_question.model_dump(exclude_none=True))

        if pre_search.decision == "ask":
            with timing.measure("response_assembly"):
                reply_text = (
                    pre_search.next_question.prompt
                    if pre_search.next_question
                    else "Preciso de mais detalhes para pesquisar."
                )
                confidence = pre_search.confidence
            tool_trace = timing.build_tool_trace(
                used_tools=used_tools,
                pre_search_path=pre_search_path,
            )

            self._logger.info(
                "pre_search_validation_pending",
                extra={
                    "trace_id": payload.trace_id,
                    "conversation_id": payload.conversation_id,
                    "branch_id": payload.business.branch_id,
                    "missing_fields": pre_search.missing_fields,
                    "used_tools": used_tools,
                    "latency_ms": tool_trace.latency_ms,
                    "stage_latency_ms": tool_trace.stage_latency_ms,
                    "pre_search_path": pre_search_path,
                },
            )
            result = ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=handoff,
                confidence=confidence,
                tool_trace=tool_trace,
                conversation_state=current_state,
            )
            self._record_review_case(
                payload=payload,
                last_messages=last_messages,
                pre_search=pre_search,
                result=result,
                search_query=None,
            )
            return result

        if pre_search.decision == "handoff":
            with timing.measure("response_assembly"):
                reply_text = (
                    pre_search.next_question.prompt
                    if pre_search.next_question
                    else "Nao consegui validar os dados para pesquisa automatica."
                )
                handoff = HandoffInfo(required=True, reason="pre_search_handoff")
                confidence = pre_search.confidence
            tool_trace = timing.build_tool_trace(
                used_tools=used_tools,
                pre_search_path=pre_search_path,
            )
            result = ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=handoff,
                confidence=confidence,
                tool_trace=tool_trace,
                conversation_state=current_state,
            )
            self._record_review_case(
                payload=payload,
                last_messages=last_messages,
                pre_search=pre_search,
                result=result,
                search_query=None,
            )
            return result

        with timing.measure("response_assembly"):
            search_query = self._build_search_query(pre_search.criteria)
        if not search_query.strip():
            with timing.measure("response_assembly"):
                reply_text = "Preciso de mais detalhes para iniciar a pesquisa."
            tool_trace = timing.build_tool_trace(
                used_tools=used_tools,
                pre_search_path=pre_search_path,
            )
            result = ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=HandoffInfo(required=False, reason=None),
                confidence=max(pre_search.confidence, 0.4),
                tool_trace=tool_trace,
                conversation_state=current_state,
            )
            self._record_review_case(
                payload=payload,
                last_messages=last_messages,
                pre_search=pre_search,
                result=result,
                search_query=search_query,
            )
            return result

        used_tools.append("search_parts")
        with timing.measure("search_parts"):
            items = self._tools.search_parts(
                query=search_query,
                branch_id=payload.business.branch_id,
                criteria=pre_search.criteria,
            )

        with timing.measure("response_assembly"):
            if len(items) == 0:
                reply_text = (
                    "Nao encontrei a peca com esses dados. "
                    "Me informe modelo, ano e motorizacao para tentar novamente. "
                    "Se preferir, posso transferir para atendimento humano."
                )
                handoff = HandoffInfo(required=True, reason="no_match")
                confidence = 0.35
            elif len(items) == 1:
                item = items[0]
                reply_text = (
                    f"Encontrei {item.title} (codigo {item.item_id}). "
                    "Para garantir o encaixe, confirme motorizacao, lado e versao do veiculo."
                )
                confidence = 0.93
            else:
                item_options = [
                    {
                        "item_id": item.item_id,
                        "title": item.title,
                        "score": item.score,
                    }
                    for item in items
                ]
                reply_text = "Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca."
                actions = actions + [
                    {
                        "type": "show_items",
                        "items": item_options,
                    },
                ]
                current_state = self._build_conversation_state(
                    criteria=pre_search.criteria,
                    last_decision="search",
                    pending_slot="result_disambiguation",
                    pending_question="Refinar a selecao entre multiplos itens encontrados.",
                )
                confidence = 0.82

            locale = self._settings.default_locale
            timezone = self._settings.default_timezone
            if payload.runtime and payload.runtime.locale:
                locale = payload.runtime.locale
            if payload.runtime and payload.runtime.timezone:
                timezone = payload.runtime.timezone

        tool_trace = timing.build_tool_trace(
            used_tools=used_tools,
            pre_search_path=pre_search_path,
        )

        self._logger.info(
            "tool_search_parts_finished",
            extra={
                "trace_id": payload.trace_id,
                "conversation_id": payload.conversation_id,
                "branch_id": payload.business.branch_id,
                "results_count": len(items),
                "used_tools": used_tools,
                "latency_ms": tool_trace.latency_ms,
                "stage_latency_ms": tool_trace.stage_latency_ms,
                "pre_search_path": pre_search_path,
                "locale": locale,
                "timezone": timezone,
            },
        )

        result = ProcessResult(
            reply_text=reply_text,
            actions=actions,
            handoff=handoff,
            confidence=confidence,
            tool_trace=tool_trace,
            conversation_state=current_state,
        )
        self._record_review_case(
            payload=payload,
            last_messages=last_messages,
            pre_search=pre_search,
            result=result,
            search_query=search_query,
        )
        return result

    def _validate_pre_search(
        self,
        *,
        query: str,
        last_messages: list[dict[str, str]],
        incoming_state: ConversationState | None,
    ) -> tuple[PreSearchValidation, str, list[str]]:
        deterministic_validator = getattr(
            self._pre_search_validator,
            "try_validate_deterministically",
            None,
        )
        if (
            self._settings.pre_search_deterministic_bypass_enabled
            and callable(deterministic_validator)
        ):
            try:
                deterministic_result = deterministic_validator(
                    query,
                    last_messages=last_messages,
                    conversation_state=incoming_state,
                )
            except Exception:
                self._logger.warning(
                    "pre_search_deterministic_bypass_failed",
                    exc_info=True,
                )
            else:
                if isinstance(deterministic_result, PreSearchValidation):
                    self._logger.info(
                        "pre_search_deterministic_bypass_used",
                        extra={
                            "criteria": deterministic_result.criteria.model_dump(
                                exclude_none=True
                            ),
                        },
                    )
                    return (
                        deterministic_result,
                        "deterministic_bypass",
                        ["pre_search_deterministic"],
                    )

        deterministic_ask_validator = getattr(
            self._pre_search_validator,
            "try_validate_deterministic_ask",
            None,
        )
        if (
            self._settings.pre_search_deterministic_ask_enabled
            and callable(deterministic_ask_validator)
        ):
            try:
                deterministic_ask_result = deterministic_ask_validator(
                    query,
                    last_messages=last_messages,
                    conversation_state=incoming_state,
                )
            except Exception:
                self._logger.warning(
                    "pre_search_deterministic_ask_failed",
                    exc_info=True,
                )
            else:
                if (
                    isinstance(deterministic_ask_result, PreSearchValidation)
                    and deterministic_ask_result.decision == "ask"
                    and bool(deterministic_ask_result.missing_fields)
                    and deterministic_ask_result.next_question is not None
                    and deterministic_ask_result.next_question.key
                    == deterministic_ask_result.missing_fields[0]
                ):
                    self._logger.info(
                        "pre_search_deterministic_ask_used",
                        extra={
                            "criteria": deterministic_ask_result.criteria.model_dump(
                                exclude_none=True
                            ),
                            "missing_fields": deterministic_ask_result.missing_fields,
                            "next_question_key": (
                                deterministic_ask_result.next_question.key
                            ),
                        },
                    )
                    return (
                        deterministic_ask_result,
                        "deterministic_ask",
                        ["pre_search_deterministic_ask"],
                    )

        return (
            self._pre_search_validator.validate(
                query,
                last_messages=last_messages,
                conversation_state=incoming_state,
            ),
            "llm",
            ["pre_search_validator"],
        )

    @staticmethod
    def _build_search_query(criteria: SearchCriteria) -> str:
        tokens = [
            criteria.part_code,
            criteria.part_query,
            criteria.vehicle_brand,
            criteria.vehicle_model,
            str(criteria.vehicle_year) if criteria.vehicle_year else None,
            criteria.engine,
            "esquerdo" if criteria.side == "left" else "direito" if criteria.side == "right" else None,
            "dianteiro" if criteria.position == "front" else "traseiro" if criteria.position == "rear" else None,
            "eixo dianteiro" if criteria.axle == "front" else "eixo traseiro" if criteria.axle == "rear" else None,
            criteria.variant,
        ]
        return " ".join(token for token in tokens if token)

    def _canonicalize_validated_part_query(
        self,
        pre_search: PreSearchValidation,
    ) -> PreSearchValidation:
        part_query = pre_search.criteria.part_query
        if not part_query:
            return pre_search

        canonicalizer = getattr(
            self._pre_search_validator,
            "canonicalize_part_query",
            None,
        )
        if not callable(canonicalizer):
            return pre_search

        canonical_part_query = canonicalizer(part_query)
        if canonical_part_query == part_query:
            return pre_search

        criteria_values = pre_search.criteria.model_dump(exclude_none=False)
        criteria_values["part_query"] = canonical_part_query
        criteria = SearchCriteria.model_validate(criteria_values)

        decision = pre_search.decision
        missing_fields = [
            field for field in pre_search.missing_fields if field != "part_query"
        ]
        next_question = pre_search.next_question

        if canonical_part_query is None and not criteria.part_code:
            decision = "handoff"
            missing_fields = []
            next_question = NextQuestion(
                key="handoff",
                prompt=UNSUPPORTED_PART_HANDOFF_PROMPT,
            )

        return PreSearchValidation(
            decision=decision,
            criteria=criteria,
            missing_fields=missing_fields,
            next_question=next_question,
            confidence=pre_search.confidence,
        )

    def _enforce_part_code_provenance(
        self,
        pre_search: PreSearchValidation,
        *,
        message_text: str,
        last_messages: list[dict[str, str]],
    ) -> PreSearchValidation:
        part_code = normalize_part_code_candidate(pre_search.criteria.part_code)
        if not part_code:
            return pre_search

        literal_evidence = has_literal_part_code_evidence(
            part_code,
            message_text=message_text,
            last_messages=last_messages,
        )
        extractor_evidence = self._part_code_validated_by_extractor(
            part_code=part_code,
            message_text=message_text,
            last_messages=last_messages,
        )
        if literal_evidence or extractor_evidence:
            if part_code == pre_search.criteria.part_code:
                return pre_search
            criteria_values = pre_search.criteria.model_dump(exclude_none=False)
            criteria_values["part_code"] = part_code
            return PreSearchValidation(
                decision=pre_search.decision,
                criteria=SearchCriteria.model_validate(criteria_values),
                missing_fields=list(pre_search.missing_fields),
                next_question=pre_search.next_question,
                confidence=pre_search.confidence,
            )

        self._logger.warning(
            "part_code_rejected_without_provenance",
            extra={"part_code": part_code},
        )
        criteria_values = pre_search.criteria.model_dump(exclude_none=False)
        criteria_values["part_code"] = None
        criteria = SearchCriteria.model_validate(criteria_values)
        decision = pre_search.decision
        missing_fields = [
            field for field in pre_search.missing_fields if field != "part_code"
        ]
        next_question = pre_search.next_question
        if next_question is not None and next_question.key == "part_code":
            next_question = None

        if decision == "search" and not criteria.part_query:
            decision = "ask"
            if "part_query" not in missing_fields:
                missing_fields.insert(0, "part_query")
            next_question = NextQuestion(
                key="part_query",
                prompt="Qual peca voce precisa?",
            )

        return PreSearchValidation(
            decision=decision,
            criteria=criteria,
            missing_fields=missing_fields,
            next_question=next_question,
            confidence=pre_search.confidence,
        )

    def _part_code_validated_by_extractor(
        self,
        *,
        part_code: str,
        message_text: str,
        last_messages: list[dict[str, str]],
    ) -> bool:
        extractor = getattr(
            self._pre_search_validator,
            "extract_dictionary_seed_criteria",
            None,
        )
        if not callable(extractor):
            return False
        try:
            criteria = extractor(
                message_text=message_text,
                last_messages=last_messages,
            )
        except Exception:
            return False
        extracted_part_code = normalize_part_code_candidate(
            getattr(criteria, "part_code", None)
        )
        return extracted_part_code == part_code

    def _record_review_case(
        self,
        *,
        payload: AgentRequestV1,
        last_messages: list[dict[str, str]],
        pre_search: PreSearchValidation,
        result: ProcessResult,
        search_query: str | None,
    ) -> None:
        try:
            audit_info = self._validator_audit_info()
            self._review_recorder.record_interaction(
                trace_id=payload.trace_id,
                conversation_id=payload.conversation_id,
                branch_id=payload.business.branch_id,
                channel_name=payload.channel.name if payload.channel else None,
                schema_version=payload.schema_version,
                message_text=payload.message.text,
                last_messages=last_messages,
                predicted_decision=pre_search.decision,
                predicted_criteria=pre_search.criteria.model_dump(exclude_none=True),
                predicted_missing_fields=list(pre_search.missing_fields),
                predicted_next_question=(
                    pre_search.next_question.model_dump(exclude_none=True)
                    if pre_search.next_question is not None
                    else None
                ),
                predicted_confidence=pre_search.confidence,
                final_reply_text=result.reply_text,
                final_actions=list(result.actions),
                final_handoff_required=result.handoff.required,
                final_handoff_reason=result.handoff.reason,
                final_confidence=result.confidence,
                final_used_tools=list(result.tool_trace.used_tools),
                final_latency_ms=result.tool_trace.latency_ms,
                search_query=search_query,
                llm_model=self._settings.llm_model,
                llm_num_predict=self._settings.llm_num_predict,
                llm_endpoint_used=audit_info.get("llm_endpoint_used"),
                llm_raw_content=audit_info.get("llm_raw_content"),
                llm_output_valid=audit_info.get("llm_output_valid"),
                llm_parse_error=audit_info.get("llm_parse_error"),
                llm_fallback_used=audit_info.get("llm_fallback_used"),
                llm_decision_raw=audit_info.get("llm_decision_raw"),
            )
        except Exception:
            self._logger.warning(
                "pre_search_review_capture_failed",
                extra={
                    "trace_id": payload.trace_id,
                    "conversation_id": payload.conversation_id,
                },
            )

    def _validator_audit_info(self) -> dict[str, Any]:
        getter = getattr(self._pre_search_validator, "get_last_audit", None)
        if not callable(getter):
            return {}
        try:
            result = getter()
        except Exception:
            return {}
        if not isinstance(result, dict):
            return {}
        return result

    @staticmethod
    def _build_conversation_state(
        *,
        criteria: SearchCriteria,
        last_decision: str,
        next_question: NextQuestion | None = None,
        pending_slot: str | None = None,
        pending_question: str | None = None,
    ) -> ConversationState:
        resolved_pending_slot = pending_slot
        resolved_pending_question = pending_question

        if next_question is not None:
            resolved_pending_slot = next_question.key
            resolved_pending_question = next_question.prompt

        return ConversationState(
            criteria=criteria,
            pending_slot=resolved_pending_slot,
            pending_question=resolved_pending_question,
            last_decision=last_decision,
        )
