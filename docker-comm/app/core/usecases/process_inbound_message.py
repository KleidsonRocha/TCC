import logging

from app.config import Settings
from app.core.domain.errors import AgentBadResponseError, AgentTimeoutError, AgentUnavailableError
from app.core.domain.models import (
    AgentRequestPayload,
    BusinessInfo,
    ChannelInfo,
    ConversationContext,
    HistoryMessage,
    IncomingMessage,
    ProcessResult,
    RuntimeInfo,
)
from app.core.domain.rules import normalize_branch_id, validate_text
from app.core.ports.agent_client import AgentClient
from app.core.ports.session_store import SessionStore


class ProcessInboundMessageUseCase:
    def __init__(
        self,
        session_store: SessionStore,
        agent_client: AgentClient,
        settings: Settings,
        logger: logging.Logger,
    ) -> None:
        self._session_store = session_store
        self._agent_client = agent_client
        self._settings = settings
        self._logger = logger

    async def execute(
        self,
        *,
        source: str,
        conversation_id: str,
        text: str,
        branch_id: int | None,
        trace_id: str,
    ) -> ProcessResult:
        validate_text(text)

        normalized_branch_id, corrected = normalize_branch_id(branch_id, self._settings.default_branch_id)
        if corrected:
            self._logger.info(
                "branch_corrected",
                extra={
                    "trace_id": trace_id,
                    "conversation_id": conversation_id,
                    "branch_id_in": branch_id,
                    "branch_id_out": normalized_branch_id,
                },
            )

        history = await self._session_store.get_messages(conversation_id)
        conversation_state = await self._session_store.get_conversation_state(conversation_id)
        user_message = HistoryMessage(role="user", text=text)

        payload = AgentRequestPayload(
            trace_id=trace_id,
            conversation_id=conversation_id,
            channel=ChannelInfo(name=source),
            message=IncomingMessage(text=text),
            context=ConversationContext(
                last_messages=history,
                conversation_state=conversation_state,
            ),
            runtime=RuntimeInfo(locale="pt-BR", timezone="America/Sao_Paulo"),
            business=BusinessInfo(branch_id=normalized_branch_id),
        )

        try:
            agent_response, status_code = await self._agent_client.send(payload, trace_id)
        except (AgentTimeoutError, AgentUnavailableError, AgentBadResponseError):
            await self._session_store.append_messages(
                conversation_id=conversation_id,
                messages=[user_message],
                history_limit=self._settings.history_limit,
            )
            raise

        assistant_message = HistoryMessage(role="assistant", text=agent_response.reply)
        await self._session_store.append_messages(
            conversation_id=conversation_id,
            messages=[user_message, assistant_message],
            history_limit=self._settings.history_limit,
        )
        await self._session_store.set_conversation_state(
            conversation_id=conversation_id,
            conversation_state=agent_response.conversation_state,
        )

        if agent_response.handoff.required:
            self._logger.info(
                "handoff_required",
                extra={
                    "trace_id": trace_id,
                    "conversation_id": conversation_id,
                    "handoff_reason": agent_response.handoff.reason,
                },
            )

        return ProcessResult(
            conversation_id=conversation_id,
            trace_id=trace_id,
            reply=agent_response.reply,
            actions=agent_response.actions,
            handoff=agent_response.handoff,
            confidence=agent_response.confidence,
            agent_status_code=status_code,
            conversation_state=agent_response.conversation_state,
        )
