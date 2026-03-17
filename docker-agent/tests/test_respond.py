from fastapi.testclient import TestClient

from app.config import Settings
from app.core.domain.models import ConversationState
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.pre_search import NextQuestion, PreSearchValidation, SearchCriteria
from app.infra.pre_search_validator_llm import LLMPreSearchValidator
from app.infra.logger import configure_logging, get_logger
from app.main import create_app
from app.infra.tools_mock import MockTools


class StubPreSearchValidator:
    @staticmethod
    def _search(**criteria_kwargs: object) -> PreSearchValidation:
        return PreSearchValidation(
            decision="search",
            criteria=SearchCriteria(**criteria_kwargs),
            missing_fields=[],
            next_question=None,
            confidence=0.92,
        )

    @staticmethod
    def _ask(*, key: str, prompt: str) -> PreSearchValidation:
        return PreSearchValidation(
            decision="ask",
            criteria=SearchCriteria(),
            missing_fields=[key],
            next_question=NextQuestion(key=key, prompt=prompt),
            confidence=0.86,
        )

    def validate(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, str]] | None = None,
        conversation_state: ConversationState | None = None,
    ) -> PreSearchValidation:
        text = (message_text or "").strip().lower()
        context_text = " ".join(message.get("text", "") for message in (last_messages or [])).lower()
        _ = conversation_state

        if text == "2008" and "coxim ecosport" in context_text:
            return self._search(
                part_query="coxim",
                vehicle_model="Ecosport",
                vehicle_year=2008,
            )

        if "filtro de oleo" in text and "ecosport" in text:
            if "2008" in text or "2008" in context_text:
                return self._search(
                    part_query="filtro de oleo",
                    vehicle_model="Ecosport",
                    vehicle_year=2008,
                )

        if "filtro" in text and "filtro de oleo" not in text and "ecosport" in text:
            return self._ask(key="vehicle_year", prompt="Qual o ano do Ecosport?")

        if "bandeja" in text and "ecosport" in text:
            return self._search(
                part_query="bandeja",
                vehicle_model="Ecosport",
                vehicle_year=2008,
            )

        if "pastilha de freio" in text and "ecosport" in text:
            return self._search(
                part_query="pastilha de freio",
                vehicle_model="Ecosport",
                vehicle_year=2008,
            )

        return self._ask(key="part_query", prompt="Qual peca voce precisa?")


def _catalog_fixture() -> PreSearchCatalog:
    return PreSearchCatalog(
        part_patterns=[("bandeja", ("bandeja",))],
        brand_aliases={"Ford": ("ford",)},
        model_aliases={"EcoSport": ("ecosport",)},
        invalid_slot_tokens={"nao"},
        generic_ambiguous_parts={"filtro"},
        needs_side={"bandeja"},
        needs_position=set(),
        needs_axle=set(),
        needs_engine=set(),
        needs_variant=set(),
        engine_by_model={"ecosport": ["1.6", "2.0", "Nao sei"]},
    )


def _make_app():
    settings = Settings(
        LOG_LEVEL="INFO",
        APP_ENV="test",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
    )
    return create_app(
        settings_override=settings,
        pre_search_validator_override=StubPreSearchValidator(),
        tools_override=MockTools(),
    )


def _payload(
    text: str,
    schema_version: str = "1.0",
    context_messages: list[dict[str, str]] | None = None,
    conversation_state: dict | None = None,
) -> dict:
    return {
        "schema_version": schema_version,
        "trace_id": "trace-123",
        "conversation_id": "conv-001",
        "channel": {"name": "generic"},
        "message": {"text": text},
        "context": {
            "last_messages": context_messages or [],
            "conversation_state": conversation_state,
        },
        "runtime": {"locale": "pt-BR", "timezone": "America/Sao_Paulo"},
        "business": {"branch_id": 1},
    }


def test_health_returns_ok() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_respond_with_bandeja_returns_request_info() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Preciso de bandeja da EcoSport 2008"))

    assert response.status_code == 200
    body = response.json()
    assert body["reply"]["text"]
    assert body["actions"][0]["type"] == "show_items"
    assert body["conversation_state"]["pending_slot"] == "result_disambiguation"
    assert body["tool_trace"]["used_tools"] == ["pre_search_validator", "search_parts"]
    assert body["handoff"]["required"] is False


def test_respond_with_filtro_de_oleo_returns_single_match() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Quero 2 unidade do filtro de oleo para ecosport 2008"))

    assert response.status_code == 200
    body = response.json()
    assert "codigo" in body["reply"]["text"]
    assert body["actions"] == []
    assert body["handoff"]["required"] is False


def test_respond_without_match_requests_handoff() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Preciso de pastilha de freio para ecosport 2008"))

    assert response.status_code == 200
    body = response.json()
    assert body["handoff"]["required"] is True
    assert body["handoff"]["reason"] == "no_match"


def test_respond_with_generic_filter_requests_vehicle_year() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Quero 2 unidade do filtro para ecosport"))

    assert response.status_code == 200
    body = response.json()
    assert body["actions"][0]["type"] == "request_info"
    assert body["actions"][0]["key"] == "vehicle_year"
    assert body["conversation_state"]["pending_slot"] == "vehicle_year"
    assert body["tool_trace"]["used_tools"] == ["pre_search_validator"]
    assert body["handoff"]["required"] is False


def test_respond_uses_last_messages_to_complete_year() -> None:
    app = _make_app()
    context_messages = [{"role": "user", "text": "2008"}]
    with TestClient(app) as client:
        response = client.post(
            "/respond",
            json=_payload(
                "Quero 2 unidade do filtro de oleo para ecosport",
                context_messages=context_messages,
            ),
        )

    assert response.status_code == 200
    body = response.json()
    assert "codigo" in body["reply"]["text"]
    assert body["actions"] == []
    assert body["tool_trace"]["used_tools"] == ["pre_search_validator", "search_parts"]
    assert body["handoff"]["required"] is False


def test_respond_uses_previous_user_question_when_current_message_has_only_year() -> None:
    app = _make_app()
    context_messages = [
        {"role": "user", "text": "coxim ecosport"},
        {"role": "assistant", "text": "Qual o ano do veiculo?"},
    ]
    with TestClient(app) as client:
        response = client.post(
            "/respond",
            json=_payload(
                "2008",
                context_messages=context_messages,
            ),
        )

    assert response.status_code == 200
    body = response.json()
    assert "codigo" in body["reply"]["text"]
    assert body["actions"] == []
    assert body["tool_trace"]["used_tools"] == ["pre_search_validator", "search_parts"]
    assert body["handoff"]["required"] is False


def test_respond_accepts_conversation_state_in_context() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post(
            "/respond",
            json=_payload(
                "2008",
                context_messages=[
                    {"role": "user", "text": "coxim ecosport"},
                ],
                conversation_state={
                    "criteria": {
                        "part_query": "coxim",
                        "vehicle_model": "Ecosport",
                    },
                    "pending_slot": "vehicle_year",
                    "pending_question": "Qual o ano do veiculo?",
                    "last_decision": "ask",
                },
            ),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_state"]["criteria"]["vehicle_year"] == 2008


def test_respond_rejects_invalid_schema_version() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Oi", schema_version="2.0"))

    assert response.status_code == 400
    assert "schema_version" in response.json()["detail"]


def test_respond_rejects_empty_message() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("   "))

    assert response.status_code == 400
    assert "message.text" in response.json()["detail"]


def test_respond_returns_503_when_llm_pre_search_is_unavailable() -> None:
    settings = Settings(
        LOG_LEVEL="INFO",
        APP_ENV="test",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
        catalog_db_enabled=False,
        LLM_BASE_URL="http://127.0.0.1:1",
        LLM_MODEL="deepseek-r1:8b",
        LLM_TIMEOUT_MS=1000,
    )
    configure_logging(settings.log_level)
    llm_validator = LLMPreSearchValidator(
        settings=settings,
        logger=get_logger("test"),
        catalog=_catalog_fixture(),
    )
    app = create_app(
        settings_override=settings,
        pre_search_validator_override=llm_validator,
    )
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("quero bandeja ecosport 2008"))

    assert response.status_code == 503
    assert "indisponivel" in response.json()["detail"].lower()
