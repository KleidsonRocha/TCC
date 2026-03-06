import logging
import time

from app.api.schemas.contract_v1 import AgentRequestV1
from app.config import Settings
from app.core.domain.models import HandoffInfo, ProcessResult, ToolTrace
from app.core.domain.pre_search import SearchCriteria
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.core.ports.pre_search_validator import PreSearchValidatorPort
from app.core.ports.tools import ToolsPort


class ProcessAgentRequestUseCase:
    def __init__(
        self,
        *,
        tools: ToolsPort,
        pre_search_validator: PreSearchValidatorPort,
        settings: Settings,
        logger: logging.Logger,
    ) -> None:
        self._tools = tools
        self._pre_search_validator = pre_search_validator
        self._settings = settings
        self._logger = logger

    async def execute(self, payload: AgentRequestV1) -> ProcessResult:
        validate_schema_version(payload.schema_version)
        query = validate_message_text(payload.message.text)
        last_messages: list[dict[str, str]] = []
        if payload.context:
            last_messages = [
                {"role": message.role, "text": message.text}
                for message in payload.context.last_messages
            ]

        started_at = time.perf_counter()
        used_tools = ["pre_search_validator"]
        pre_search = self._pre_search_validator.validate(
            query,
            last_messages=last_messages,
        )

        actions: list[dict[str, object]] = []
        handoff = HandoffInfo(required=False, reason=None)
        confidence = 0.0

        if pre_search.next_question:
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
            return ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=handoff,
                confidence=confidence,
                tool_trace=ToolTrace(used_tools=used_tools, latency_ms=latency_ms),
            )

        if pre_search.decision == "handoff":
            reply_text = (
                pre_search.next_question.prompt
                if pre_search.next_question
                else "Nao consegui validar os dados para pesquisa automatica."
            )
            handoff = HandoffInfo(required=True, reason="pre_search_handoff")
            confidence = pre_search.confidence
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            return ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=handoff,
                confidence=confidence,
                tool_trace=ToolTrace(used_tools=used_tools, latency_ms=latency_ms),
            )

        used_tools.append("search_parts")
        search_query = self._build_search_query(pre_search.criteria)
        if not search_query.strip():
            reply_text = "Preciso de mais detalhes para iniciar a pesquisa."
            return ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=HandoffInfo(required=False, reason=None),
                confidence=max(pre_search.confidence, 0.4),
                tool_trace=ToolTrace(
                    used_tools=used_tools,
                    latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
                ),
            )

        items = self._tools.search_parts(
            query=search_query,
            branch_id=payload.business.branch_id,
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
            reply_text = "Encontrei mais de uma opcao. Pode me confirmar a motorizacao?"
            result_actions: list[dict[str, object]] = [
                {
                    "type": "request_info",
                    "key": "engine",
                    "prompt": "Qual a motorizacao do veiculo?",
                    "options": ["1.6", "2.0", "Nao sei"],
                },
                {
                    "type": "show_items",
                    "items": item_options,
                },
            ]
            if actions:
                result_actions = actions + result_actions
            actions = result_actions
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

        return ProcessResult(
            reply_text=reply_text,
            actions=actions,
            handoff=handoff,
            confidence=confidence,
            tool_trace=ToolTrace(used_tools=used_tools, latency_ms=latency_ms),
        )

    @staticmethod
    def _build_search_query(criteria: SearchCriteria) -> str:
        tokens = [
            criteria.part_code,
            criteria.part_query,
            criteria.vehicle_model,
            str(criteria.vehicle_year) if criteria.vehicle_year else None,
            criteria.engine,
            "esquerdo" if criteria.side == "left" else "direito" if criteria.side == "right" else None,
            "dianteiro" if criteria.position == "front" else "traseiro" if criteria.position == "rear" else None,
        ]
        return " ".join(token for token in tokens if token)
