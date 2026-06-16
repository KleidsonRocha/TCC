import logging
import time
from typing import Any

from app.api.schemas.contract_v1 import AgentRequestV1
from app.config import Settings
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

        started_at = time.perf_counter()
        used_tools = ["pre_search_validator"]
        pre_search = self._pre_search_validator.validate(
            query,
            last_messages=last_messages,
            conversation_state=incoming_state,
        )
        pre_search = self._canonicalize_validated_part_query(pre_search)
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
            reply_text = (
                pre_search.next_question.prompt
                if pre_search.next_question
                else "Preciso de mais detalhes para pesquisar."
            )
            confidence = pre_search.confidence
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

            self._logger.info(
                "pre_search_validation_pending",
                extra={
                    "trace_id": payload.trace_id,
                    "conversation_id": payload.conversation_id,
                    "branch_id": payload.business.branch_id,
                    "missing_fields": pre_search.missing_fields,
                    "used_tools": used_tools,
                    "latency_ms": latency_ms,
                },
            )
            result = ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=handoff,
                confidence=confidence,
                tool_trace=ToolTrace(used_tools=used_tools, latency_ms=latency_ms),
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
            reply_text = (
                pre_search.next_question.prompt
                if pre_search.next_question
                else "Nao consegui validar os dados para pesquisa automatica."
            )
            handoff = HandoffInfo(required=True, reason="pre_search_handoff")
            confidence = pre_search.confidence
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            result = ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=handoff,
                confidence=confidence,
                tool_trace=ToolTrace(used_tools=used_tools, latency_ms=latency_ms),
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

        used_tools.append("search_parts")
        search_query = self._build_search_query(pre_search.criteria)
        if not search_query.strip():
            reply_text = "Preciso de mais detalhes para iniciar a pesquisa."
            result = ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=HandoffInfo(required=False, reason=None),
                confidence=max(pre_search.confidence, 0.4),
                tool_trace=ToolTrace(
                    used_tools=used_tools,
                    latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
                ),
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

        items = self._tools.search_parts(
            query=search_query,
            branch_id=payload.business.branch_id,
            criteria=pre_search.criteria,
        )

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

        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

        locale = self._settings.default_locale
        timezone = self._settings.default_timezone
        if payload.runtime and payload.runtime.locale:
            locale = payload.runtime.locale
        if payload.runtime and payload.runtime.timezone:
            timezone = payload.runtime.timezone

        self._logger.info(
            "tool_search_parts_finished",
            extra={
                "trace_id": payload.trace_id,
                "conversation_id": payload.conversation_id,
                "branch_id": payload.business.branch_id,
                "results_count": len(items),
                "used_tools": used_tools,
                "latency_ms": latency_ms,
                "locale": locale,
                "timezone": timezone,
            },
        )

        result = ProcessResult(
            reply_text=reply_text,
            actions=actions,
            handoff=handoff,
            confidence=confidence,
            tool_trace=ToolTrace(used_tools=used_tools, latency_ms=latency_ms),
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
