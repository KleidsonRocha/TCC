import asyncio
import logging

from app.config import Settings
from app.core.domain.models import (
    AgentRequestPayload,
    AgentResponsePayload,
    BusinessInfo,
    ChannelInfo,
    ConversationContext,
    ConversationState,
    HandoffInfo,
    HistoryMessage,
    IncomingMessage,
    RuntimeInfo,
    SearchCriteriaState,
)
from app.core.usecases.process_inbound_message import ProcessInboundMessageUseCase
from app.infra.agent_client_http import HttpAgentClient


class _FakeSessionStore:
    def __init__(self) -> None:
        self.messages: list[HistoryMessage] = []
        self.conversation_state: ConversationState | None = None
        self.appended_batches: list[list[HistoryMessage]] = []
        self.saved_state: ConversationState | None = None

    async def get_messages(self, conversation_id: str) -> list[HistoryMessage]:
        _ = conversation_id
        return list(self.messages)

    async def get_conversation_state(self, conversation_id: str) -> ConversationState | None:
        _ = conversation_id
        return self.conversation_state

    async def append_messages(
        self,
        conversation_id: str,
        messages: list[HistoryMessage],
        history_limit: int,
    ) -> None:
        _ = conversation_id
        merged = self.messages + messages
        self.messages = merged[-history_limit:]
        self.appended_batches.append(messages)

    async def set_conversation_state(
        self,
        conversation_id: str,
        conversation_state: ConversationState | None,
    ) -> None:
        _ = conversation_id
        self.conversation_state = conversation_state
        self.saved_state = conversation_state

    async def close(self) -> None:
        return None


class _FakeAgentClient:
    def __init__(self, response: AgentResponsePayload) -> None:
        self.response = response
        self.last_payload = None

    async def send(self, payload, trace_id: str):
        _ = trace_id
        self.last_payload = payload
        return self.response, 200


def test_process_inbound_message_forwards_and_persists_conversation_state() -> None:
    session_store = _FakeSessionStore()
    session_store.messages = [HistoryMessage(role="user", text="quero batentes da ecosport")]
    session_store.conversation_state = ConversationState(
        criteria=SearchCriteriaState(part_query="batentes", vehicle_model="Ecosport"),
        pending_slot="engine",
        pending_question="Qual a motorizacao do veiculo?",
        last_decision="ask",
    )
    agent_client = _FakeAgentClient(
        AgentResponsePayload(
            reply="A peca e dianteira ou traseira?",
            actions=[
                {
                    "type": "request_info",
                    "key": "position",
                    "prompt": "A peca e dianteira ou traseira?",
                    "options": ["Dianteiro", "Traseiro", "Nao sei"],
                }
            ],
            handoff=HandoffInfo(required=False, reason=None),
            confidence=0.91,
            conversation_state=ConversationState(
                criteria=SearchCriteriaState(
                    part_query="batentes",
                    vehicle_model="Ecosport",
                    engine="1.6",
                ),
                pending_slot="position",
                pending_question="A peca e dianteira ou traseira?",
                last_decision="ask",
            ),
        )
    )
    use_case = ProcessInboundMessageUseCase(
        session_store=session_store,
        agent_client=agent_client,
        settings=Settings(
            AGENT_URL="http://agent.local/respond",
            REDIS_URL="redis://localhost:6379/0",
        ),
        logger=logging.getLogger("test"),
    )

    result = asyncio.run(
        use_case.execute(
            source="whatsapp",
            conversation_id="whatsapp:conv-123",
            text="1.6",
            branch_id=1,
            trace_id="trace-123",
        )
    )

    assert agent_client.last_payload is not None
    assert agent_client.last_payload.context.conversation_state is not None
    assert agent_client.last_payload.context.conversation_state.pending_slot == "engine"
    assert result.conversation_state is not None
    assert result.conversation_state.pending_slot == "position"
    assert session_store.saved_state is not None
    assert session_store.saved_state.pending_slot == "position"
    assert len(session_store.appended_batches) == 1
    assert [message.role for message in session_store.appended_batches[0]] == ["user", "assistant"]


def test_http_agent_client_parses_conversation_state() -> None:
    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "reply": {"text": "Qual a motorizacao do veiculo?"},
                "actions": [
                    {
                        "type": "request_info",
                        "key": "engine",
                        "prompt": "Qual a motorizacao do veiculo?",
                        "options": ["1.6", "2.0", "Nao sei"],
                    }
                ],
                "handoff": {"required": False, "reason": None},
                "confidence": 0.88,
                "conversation_state": {
                    "criteria": {"part_query": "batentes", "vehicle_model": "Ecosport"},
                    "pending_slot": "engine",
                    "pending_question": "Qual a motorizacao do veiculo?",
                    "last_decision": "ask",
                },
            }

    class _FakeHttpClient:
        async def post(self, url, json, headers):
            _ = url
            _ = json
            _ = headers
            return _FakeResponse()

        async def aclose(self) -> None:
            return None

    client = HttpAgentClient(
        agent_url="http://agent.local/respond",
        timeout_seconds=1.0,
        retry_count=0,
    )
    client._client = _FakeHttpClient()

    payload = AgentRequestPayload(
        trace_id="trace-1",
        conversation_id="conv-1",
        channel=ChannelInfo(name="generic"),
        message=IncomingMessage(text="oi"),
        context=ConversationContext(last_messages=[]),
        runtime=RuntimeInfo(locale="pt-BR", timezone="America/Sao_Paulo"),
        business=BusinessInfo(branch_id=1),
    )

    parsed, status_code = asyncio.run(
        client.send(
            payload=payload,
            trace_id="trace-1",
        )
    )

    assert status_code == 200
    assert parsed.conversation_state is not None
    assert parsed.conversation_state.pending_slot == "engine"
