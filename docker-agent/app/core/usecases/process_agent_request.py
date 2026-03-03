import logging
import time

from app.api.schemas.contract_v1 import AgentRequestV1
from app.config import Settings
from app.core.domain.models import HandoffInfo, ProcessResult, ToolTrace
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.core.ports.tools import ToolsPort


class ProcessAgentRequestUseCase:
    def __init__(
        self,
        *,
        tools: ToolsPort,
        settings: Settings,
        logger: logging.Logger,
    ) -> None:
        self._tools = tools
        self._settings = settings
        self._logger = logger

    async def execute(self, payload: AgentRequestV1) -> ProcessResult:
        validate_schema_version(payload.schema_version)
        query = validate_message_text(payload.message.text)

        started_at = time.perf_counter()
        used_tools = ["search_parts"]

        items = self._tools.search_parts(
            query=query,
            branch_id=payload.business.branch_id,
        )

        actions: list[dict[str, object]] = []
        handoff = HandoffInfo(required=False, reason=None)
        confidence = 0.0

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
            actions = [
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
