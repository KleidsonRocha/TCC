import logging
import asyncio

from app.api.schemas.contract_v1 import AgentRequestV1
from app.config import Settings
from app.core.domain.pre_search import NextQuestion, PreSearchValidation, SearchCriteria
from app.core.usecases.process_agent_request import ProcessAgentRequestUseCase
from app.infra.tools_mock import MockTools


class _StubValidator:
    def validate(self, message_text: str, *, last_messages=None) -> PreSearchValidation:
        return PreSearchValidation(
            decision="ask",
            criteria=SearchCriteria(part_query="radiador", vehicle_model="Gol", vehicle_year=2010),
            missing_fields=["engine"],
            next_question=NextQuestion(
                key="engine",
                prompt="Qual a motorizacao do veiculo?",
                options=["1.0", "1.6", "Nao sei"],
            ),
            confidence=0.91,
        )

    def get_last_audit(self) -> dict:
        return {
            "llm_endpoint_used": "/api/chat",
            "llm_raw_content": '{"decision":"ask"}',
            "llm_output_valid": True,
            "llm_parse_error": None,
            "llm_fallback_used": False,
            "llm_decision_raw": "ask",
        }


class _SpyRecorder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def record_interaction(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _SpyTools(MockTools):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def search_parts(self, query: str, branch_id: int):
        self.calls.append({"query": query, "branch_id": branch_id})
        return super().search_parts(query=query, branch_id=branch_id)


class _HandoffValidator:
    def validate(self, message_text: str, *, last_messages=None) -> PreSearchValidation:
        return PreSearchValidation(
            decision="handoff",
            criteria=SearchCriteria(part_query="radiador", vehicle_model="Gol"),
            missing_fields=["engine"],
            next_question=NextQuestion(
                key="handoff",
                prompt="Vou encaminhar para atendimento humano.",
            ),
            confidence=0.41,
        )

    def get_last_audit(self) -> dict:
        return {
            "llm_endpoint_used": "/api/chat",
            "llm_raw_content": '{"decision":"handoff"}',
            "llm_output_valid": True,
            "llm_parse_error": None,
            "llm_fallback_used": False,
            "llm_decision_raw": "handoff",
        }


def test_process_agent_request_records_review_capture() -> None:
    recorder = _SpyRecorder()
    use_case = ProcessAgentRequestUseCase(
        tools=MockTools(),
        pre_search_validator=_StubValidator(),
        settings=Settings(
            LOG_LEVEL="INFO",
            APP_ENV="test",
            AGENT_PORT=8001,
            DEFAULT_LOCALE="pt-BR",
            DEFAULT_TIMEZONE="America/Sao_Paulo",
        ),
        logger=logging.getLogger("test"),
        review_recorder=recorder,
    )

    payload = AgentRequestV1.model_validate(
        {
            "schema_version": "1.0",
            "trace_id": "trace-123",
            "conversation_id": "conv-001",
            "message": {"text": "radiador gol 2010"},
            "business": {"branch_id": 1},
            "channel": {"name": "whatsapp"},
            "context": {"last_messages": []},
        }
    )

    asyncio.run(use_case.execute(payload))

    assert len(recorder.calls) == 1
    assert recorder.calls[0]["predicted_decision"] == "ask"
    assert recorder.calls[0]["message_text"] == "radiador gol 2010"
    assert recorder.calls[0]["final_reply_text"] == "Qual a motorizacao do veiculo?"
    assert recorder.calls[0]["llm_endpoint_used"] == "/api/chat"
    assert recorder.calls[0]["llm_raw_content"] == '{"decision":"ask"}'
    assert recorder.calls[0]["llm_output_valid"] is True
    assert recorder.calls[0]["llm_fallback_used"] is False
    assert recorder.calls[0]["llm_decision_raw"] == "ask"


def test_process_agent_request_handoff_skips_search_tools() -> None:
    tools = _SpyTools()
    recorder = _SpyRecorder()
    use_case = ProcessAgentRequestUseCase(
        tools=tools,
        pre_search_validator=_HandoffValidator(),
        settings=Settings(
            LOG_LEVEL="INFO",
            APP_ENV="test",
            AGENT_PORT=8001,
            DEFAULT_LOCALE="pt-BR",
            DEFAULT_TIMEZONE="America/Sao_Paulo",
        ),
        logger=logging.getLogger("test"),
        review_recorder=recorder,
    )

    payload = AgentRequestV1.model_validate(
        {
            "schema_version": "1.0",
            "trace_id": "trace-456",
            "conversation_id": "conv-002",
            "message": {"text": "radiador gol 2010"},
            "business": {"branch_id": 1},
            "channel": {"name": "whatsapp"},
            "context": {"last_messages": []},
        }
    )

    result = asyncio.run(use_case.execute(payload))

    assert result.handoff.required is True
    assert result.handoff.reason == "pre_search_handoff"
    assert result.tool_trace.used_tools == ["pre_search_validator"]
    assert tools.calls == []
    assert recorder.calls[0]["final_handoff_reason"] == "pre_search_handoff"
    assert recorder.calls[0]["llm_decision_raw"] == "handoff"


def test_build_search_query_includes_structured_vehicle_tokens() -> None:
    query = ProcessAgentRequestUseCase._build_search_query(
        SearchCriteria(
            part_code="AB-1234",
            part_query="bandeja",
            vehicle_brand="Ford",
            vehicle_model="Ecosport",
            vehicle_year=2008,
            engine="1.6",
            side="left",
            position="front",
            axle="rear",
            variant="XLS",
        )
    )

    assert query == "AB-1234 bandeja Ford Ecosport 2008 1.6 esquerdo dianteiro eixo traseiro XLS"
