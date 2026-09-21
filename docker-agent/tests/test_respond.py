import asyncio
import time
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.domain.errors import SearchPartsServiceUnavailableError
from app.core.domain.models import ConversationState
from app.core.domain.models import PartItem
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.pre_search import NextQuestion, PreSearchValidation, SearchCriteria
from app.core.ports.tools import ToolsPort
from app.core.usecases.process_agent_request import ProcessAgentRequestUseCase
from app.infra.pre_search_validator_llm import LLMPreSearchValidator
from app.infra.logger import configure_logging, get_logger
from app.main import create_app


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

    def extract_dictionary_seed_criteria(
        self,
        *,
        message_text: str,
        last_messages: list[dict[str, str]] | None = None,
    ) -> SearchCriteria:
        _ = last_messages
        text = (message_text or "").lower()
        if "pastilha de freio" in text:
            return SearchCriteria(part_query="pastilha de freio")
        if "bandeja" in text:
            return SearchCriteria(part_query="bandeja")
        return SearchCriteria()

    def extract_dictionary_seed_criteria(
        self,
        *,
        message_text: str,
        last_messages: list[dict[str, str]] | None = None,
    ) -> SearchCriteria:
        _ = last_messages
        text = (message_text or "").lower()
        if "pastilha de freio" in text:
            return SearchCriteria(part_query="pastilha de freio")
        if "bandeja" in text:
            return SearchCriteria(part_query="bandeja")
        return SearchCriteria()


class _FakeTools(ToolsPort):
    def search_parts(self, query: str, branch_id: int, criteria: SearchCriteria | None = None) -> list[PartItem]:
        normalized = (query or "").lower()
        _ = branch_id
        _ = criteria

        if "bandeja" in normalized:
            return [
                PartItem(
                    item_id="BDJ-001",
                    title="Bandeja dianteira lado esquerdo",
                    score=0.91,
                    attributes={"side": ["Esquerdo"]},
                ),
                PartItem(
                    item_id="BDJ-002",
                    title="Bandeja dianteira lado direito",
                    score=0.89,
                    attributes={"side": ["Direito"]},
                ),
            ] + [PartItem(item_id=f"BDJ-{i:03}", title="Bandeja direita", score=.8,
                          attributes={"side": ["Direito"]}) for i in range(3, 12)]
        if "filtro de oleo" in normalized:
            return [PartItem(item_id="FLT-010", title="Filtro de oleo motor 1.6", score=0.96)]
        if "coxim" in normalized:
            return [PartItem(item_id="CXM-101", title="Coxim do motor dianteiro", score=0.92)]
        return []


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
        tools_override=_FakeTools(),
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


def test_ready_reports_dependency_state_without_changing_health(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _degraded(_settings):
        return {
            "status": "degraded",
            "dependencies": {
                "catalog": {"status": "ready"},
                "erp": {"status": "unavailable"},
                "inference": {"status": "ready"},
            },
        }

    monkeypatch.setattr("app.api.routes.health.check_readiness_async", _degraded)
    with TestClient(_make_app()) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 503
    assert ready.json()["status"] == "degraded"
    assert ready.json()["dependencies"]["erp"]["status"] == "unavailable"


def test_production_requires_review_and_gateway_secrets() -> None:
    app = create_app(
        settings_override=Settings(
            APP_ENV="production",
            CATALOG_DB_ENABLED=False,
            LLM_WARMUP_ENABLED=False,
        ),
        pre_search_validator_override=StubPreSearchValidator(),
        tools_override=_FakeTools(),
    )

    with pytest.raises(RuntimeError, match="REVIEW_API_KEY"):
        with TestClient(app):
            pass


def test_production_requires_gateway_key_for_caller_supplied_context() -> None:
    app = create_app(
        settings_override=Settings(
            APP_ENV="production",
            CATALOG_DB_ENABLED=False,
            LLM_WARMUP_ENABLED=False,
            REVIEW_API_KEY="review-secret",
            RESPOND_GATEWAY_API_KEY="gateway-secret",
        ),
        pre_search_validator_override=StubPreSearchValidator(),
        tools_override=_FakeTools(),
    )
    payload = _payload(
        "2008",
        context_messages=[{"role": "user", "text": "coxim ecosport"}],
    )

    with TestClient(app) as client:
        denied = client.post("/respond", json=payload)
        allowed = client.post(
            "/respond",
            json=payload,
            headers={"X-Agent-Gateway-Key": "gateway-secret"},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_respond_rejects_oversized_state_and_history() -> None:
    app = _make_app()
    oversized_history = _payload(
        "oi",
        context_messages=[{"role": "user", "text": "mensagem"}] * 21,
    )
    oversized_state = _payload(
        "oi",
        conversation_state={
            "result_disambiguation": {
                "question_key": "side",
                "prompt": "Qual lado?",
                "candidates": [
                    {"item_id": f"item-{index}", "title": "Item", "score": 0.5}
                    for index in range(51)
                ],
            },
        },
    )

    with TestClient(app) as client:
        history_response = client.post("/respond", json=oversized_history)
        state_response = client.post("/respond", json=oversized_state)

    assert history_response.status_code == 422
    assert state_response.status_code == 422


def test_respond_with_bandeja_starts_result_disambiguation() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Preciso de bandeja da EcoSport 2008"))

    assert response.status_code == 200
    body = response.json()
    assert body["reply"]["text"]
    assert body["actions"] == [
        {
            "type": "request_info",
            "key": "result_disambiguation",
            "prompt": "Os resultados diferem em lado: Direito; Esquerdo. Qual opcao corresponde ao que voce procura?",
            "options": ["1 - Direito", "2 - Esquerdo", "Nenhuma dessas"],
        }
    ]
    assert body["conversation_state"]["pending_slot"] == "result_disambiguation"
    assert body["conversation_state"]["result_disambiguation"]["question_key"] == "side"
    assert body["tool_trace"]["used_tools"] == ["pre_search_validator", "search_parts"]
    assert body["tool_trace"]["pre_search_path"] == "llm"
    assert set(body["tool_trace"]["stage_latency_ms"]) == {
        "pre_search_validator",
        "search_parts",
        "response_assembly",
    }
    assert body["handoff"]["required"] is False


def test_respond_selects_result_in_follow_up_without_new_erp_search() -> None:
    app = _make_app()
    with TestClient(app) as client:
        first = client.post(
            "/respond",
            json=_payload("Preciso de bandeja da EcoSport 2008"),
        ).json()
        second = client.post(
            "/respond",
            json=_payload(
                "esquerdo",
                context_messages=[
                    {"role": "user", "text": "Preciso de bandeja da EcoSport 2008"},
                    {"role": "assistant", "text": first["reply"]["text"]},
                ],
                conversation_state=first["conversation_state"],
            ),
        )

    assert second.status_code == 200
    body = second.json()
    assert "BDJ-001" in body["reply"]["text"]
    assert body["actions"][0]["type"] == "show_items"
    assert body["actions"][0]["items"][0]["item_id"] == "BDJ-001"
    assert body["tool_trace"]["pre_search_path"] == "result_disambiguation"
    assert body["tool_trace"]["used_tools"] == ["result_disambiguation"]
    assert "search_parts" not in body["tool_trace"]["used_tools"]
    assert body["conversation_state"]["pending_slot"] is None
    assert body["conversation_state"]["result_disambiguation"] is None


def test_respond_change_of_part_clears_result_disambiguation() -> None:
    app = _make_app()
    with TestClient(app) as client:
        first = client.post(
            "/respond",
            json=_payload("Preciso de bandeja da EcoSport 2008"),
        ).json()
        second = client.post(
            "/respond",
            json=_payload(
                "Preciso de pastilha de freio para ecosport 2008",
                conversation_state=first["conversation_state"],
            ),
        )

    assert second.status_code == 200
    body = second.json()
    assert body["tool_trace"]["pre_search_path"] == "llm"
    assert body["conversation_state"]["criteria"]["part_query"] == "pastilha de freio"
    assert body["conversation_state"]["result_disambiguation"] is None


def test_respond_negates_result_options_and_offers_new_search() -> None:
    app = _make_app()
    with TestClient(app) as client:
        first = client.post(
            "/respond",
            json=_payload("Preciso de bandeja da EcoSport 2008"),
        ).json()
        second = client.post(
            "/respond",
            json=_payload(
                "nenhuma dessas",
                conversation_state=first["conversation_state"],
            ),
        )

    assert second.status_code == 200
    body = second.json()
    assert "novo criterio" in body["reply"]["text"].lower()
    assert body["handoff"]["required"] is False
    assert body["conversation_state"]["pending_slot"] == "no_match_retry"
    assert body["conversation_state"]["result_disambiguation"] is None


def test_respond_handoffs_after_result_disambiguation_attempt_limit() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post(
            "/respond",
            json=_payload("Preciso de bandeja da EcoSport 2008"),
        ).json()
        for answer in ("talvez", "aquela", "indefinido"):
            response = client.post(
                "/respond",
                json=_payload(
                    answer,
                    conversation_state=response["conversation_state"],
                ),
            ).json()

    assert response["handoff"] == {
        "required": True,
        "reason": "result_disambiguation_limit",
    }
    assert response["conversation_state"]["pending_slot"] is None
    assert response["conversation_state"]["result_disambiguation"] is None


def test_respond_respects_explicit_handoff_during_result_disambiguation() -> None:
    app = _make_app()
    with TestClient(app) as client:
        first = client.post(
            "/respond",
            json=_payload("Preciso de bandeja da EcoSport 2008"),
        ).json()
        second = client.post(
            "/respond",
            json=_payload(
                "quero falar com um vendedor",
                conversation_state=first["conversation_state"],
            ),
        ).json()

    assert second["handoff"] == {
        "required": True,
        "reason": "result_disambiguation_requested",
    }


def test_respond_selects_result_in_follow_up_without_new_erp_search() -> None:
    app = _make_app()
    with TestClient(app) as client:
        first = client.post(
            "/respond",
            json=_payload("Preciso de bandeja da EcoSport 2008"),
        ).json()
        second = client.post(
            "/respond",
            json=_payload(
                "esquerdo",
                context_messages=[
                    {"role": "user", "text": "Preciso de bandeja da EcoSport 2008"},
                    {"role": "assistant", "text": first["reply"]["text"]},
                ],
                conversation_state=first["conversation_state"],
            ),
        )

    assert second.status_code == 200
    body = second.json()
    assert "BDJ-001" in body["reply"]["text"]
    assert body["actions"][0]["type"] == "show_items"
    assert body["actions"][0]["items"][0]["item_id"] == "BDJ-001"
    assert body["tool_trace"]["pre_search_path"] == "result_disambiguation"
    assert body["tool_trace"]["used_tools"] == ["result_disambiguation"]
    assert "search_parts" not in body["tool_trace"]["used_tools"]
    assert body["conversation_state"]["pending_slot"] is None
    assert body["conversation_state"]["result_disambiguation"] is None


def test_respond_change_of_part_clears_result_disambiguation() -> None:
    app = _make_app()
    with TestClient(app) as client:
        first = client.post(
            "/respond",
            json=_payload("Preciso de bandeja da EcoSport 2008"),
        ).json()
        second = client.post(
            "/respond",
            json=_payload(
                "Preciso de pastilha de freio para ecosport 2008",
                conversation_state=first["conversation_state"],
            ),
        )

    assert second.status_code == 200
    body = second.json()
    assert body["tool_trace"]["pre_search_path"] == "llm"
    assert body["conversation_state"]["criteria"]["part_query"] == "pastilha de freio"
    assert body["conversation_state"]["result_disambiguation"] is None


def test_respond_with_filtro_de_oleo_returns_single_match() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Quero 2 unidade do filtro de oleo para ecosport 2008"))

    assert response.status_code == 200
    body = response.json()
    assert "codigo" in body["reply"]["text"]
    assert body["actions"] == []
    assert body["handoff"]["required"] is False


def test_respond_without_match_offers_retry_or_handoff() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Preciso de pastilha de freio para ecosport 2008"))

    assert response.status_code == 200
    body = response.json()
    assert body["handoff"] == {"required": False, "reason": None}
    assert "criterios pesquisados" in body["reply"]["text"].lower()
    assert 'peca "pastilha de freio"' in body["reply"]["text"].lower()
    assert 'modelo "ecosport"' in body["reply"]["text"].lower()
    assert 'ano "2008"' in body["reply"]["text"].lower()
    assert "nao comprova incompatibilidade" in body["reply"]["text"].lower()
    assert "me informe modelo, ano e motorizacao" not in body["reply"]["text"].lower()
    assert body["conversation_state"]["pending_slot"] == "no_match_retry"
    assert body["conversation_state"]["last_decision"] == "no_match"


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


def test_respond_uses_deterministic_ask_without_calling_llm() -> None:
    settings = Settings(
        APP_ENV="test",
        CATALOG_DB_ENABLED=False,
        PRE_SEARCH_REVIEW_CAPTURE_ENABLED=False,
        PRE_SEARCH_DETERMINISTIC_BYPASS_ENABLED=True,
        PRE_SEARCH_DETERMINISTIC_ASK_ENABLED=True,
        LLM_WARMUP_ENABLED=False,
    )
    validator = LLMPreSearchValidator(
        settings=settings,
        logger=get_logger(),
        catalog=_catalog_fixture(),
    )

    def fail_if_llm_is_called(*args, **kwargs) -> PreSearchValidation:
        raise AssertionError("a LLM nao deveria ser chamada")

    validator.validate = fail_if_llm_is_called  # type: ignore[method-assign]
    app = create_app(
        settings_override=settings,
        pre_search_validator_override=validator,
        tools_override=_FakeTools(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/respond",
            json=_payload("Preciso de bandeja da EcoSport 2008"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"]["text"] == "Qual lado da peca?"
    assert body["actions"] == [
        {
            "type": "request_info",
            "key": "side",
            "prompt": "Qual lado da peca?",
            "options": ["Esquerdo", "Direito", "Nao sei"],
        }
    ]
    assert body["conversation_state"] == {
            "criteria": {
                "part_query": "bandeja",
                "part_code": None,
                "preferred_product_brand": None,
                "vehicle_brand": None,
            "vehicle_model": "EcoSport",
            "vehicle_year": 2008,
            "engine": None,
            "side": None,
            "position": None,
            "axle": None,
            "variant": None,
                "quantity": None,
            },
            "items": None,
            "active_item_index": None,
            "item_results": None,
            "pending_slot": "side",
            "pending_question": "Qual lado da peca?",
            "last_decision": "ask",
            "result_disambiguation": None,
        }
    assert body["tool_trace"]["pre_search_path"] == "deterministic_ask"
    assert body["tool_trace"]["used_tools"] == [
        "pre_search_deterministic_ask"
    ]


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
        PRE_SEARCH_DETERMINISTIC_ASK_ENABLED=False,
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


def test_respond_returns_503_when_single_erp_search_is_unavailable() -> None:
    class _UnavailableTools(_FakeTools):
        def search_parts(
            self,
            query: str,
            branch_id: int,
            criteria: SearchCriteria | None = None,
        ) -> list[PartItem]:
            raise SearchPartsServiceUnavailableError("ERP temporariamente indisponivel")

    app = create_app(
        settings_override=Settings(
            APP_ENV="test",
            PRE_SEARCH_REVIEW_CAPTURE_ENABLED=False,
        ),
        pre_search_validator_override=StubPreSearchValidator(),
        tools_override=_UnavailableTools(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/respond",
            json=_payload("Quero filtro de oleo para EcoSport 2008"),
        )

    assert response.status_code == 503
    assert "indisponivel" in response.json()["detail"].lower()


def test_slow_inference_does_not_block_health_or_deterministic_conversation() -> None:
    class _SlowValidator(StubPreSearchValidator):
        def try_validate_deterministically(
            self,
            message_text: str,
            *,
            last_messages=None,
            conversation_state=None,
        ) -> PreSearchValidation | None:
            _ = last_messages, conversation_state
            if message_text == "pedido deterministico":
                return self._search(
                    part_query="filtro de oleo",
                    vehicle_model="EcoSport",
                    vehicle_year=2008,
                )
            return None

        def validate(self, message_text: str, *, last_messages=None, conversation_state=None):
            if message_text == "pedido lento":
                time.sleep(0.25)
            return super().validate(
                message_text,
                last_messages=last_messages,
                conversation_state=conversation_state,
            )

    app = create_app(
        settings_override=Settings(
            APP_ENV="test",
            PRE_SEARCH_REVIEW_CAPTURE_ENABLED=False,
            LLM_WARMUP_ENABLED=False,
            LLM_TIMEOUT_MS=1000,
            LLM_MAX_CONCURRENT_REQUESTS=2,
        ),
        pre_search_validator_override=_SlowValidator(),
        tools_override=_FakeTools(),
    )

    async def exercise() -> tuple[float, float, int, int]:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                slow = asyncio.create_task(client.post("/respond", json=_payload("pedido lento")))
                await asyncio.sleep(0.03)
                health_started = time.perf_counter()
                health = await client.get("/health")
                health_elapsed = time.perf_counter() - health_started
                deterministic_started = time.perf_counter()
                deterministic = await client.post(
                    "/respond", json=_payload("pedido deterministico")
                )
                deterministic_elapsed = time.perf_counter() - deterministic_started
                slow_response = await slow
        return health_elapsed, deterministic_elapsed, health.status_code, slow_response.status_code

    health_elapsed, deterministic_elapsed, health_status, slow_status = asyncio.run(exercise())

    assert health_status == 200
    assert slow_status == 200
    assert health_elapsed < 0.1
    assert deterministic_elapsed < 0.15


def test_app_startup_runs_validator_warmup_when_enabled() -> None:
    class _WarmupValidator(StubPreSearchValidator):
        def __init__(self) -> None:
            self.warmup_calls = 0
            self.warmup_finished = Event()

        def warmup(self) -> None:
            self.warmup_calls += 1
            self.warmup_finished.set()

    validator = _WarmupValidator()
    settings = Settings(
        LOG_LEVEL="INFO",
        APP_ENV="test",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
        LLM_WARMUP_ENABLED=True,
    )
    app = create_app(
        settings_override=settings,
        pre_search_validator_override=validator,
        tools_override=_FakeTools(),
    )

    with TestClient(app):
        assert validator.warmup_finished.wait(timeout=1)

    assert validator.warmup_calls == 1


def test_health_is_available_while_warmup_runs_in_background() -> None:
    class _SlowWarmupValidator(StubPreSearchValidator):
        def __init__(self) -> None:
            self.warmup_started = Event()
            self.release_warmup = Event()

        def warmup(self) -> None:
            self.warmup_started.set()
            self.release_warmup.wait(timeout=1)

    validator = _SlowWarmupValidator()
    app = create_app(
        settings_override=Settings(
            APP_ENV="test",
            CATALOG_DB_ENABLED=False,
            LLM_WARMUP_ENABLED=True,
        ),
        pre_search_validator_override=validator,
        tools_override=_FakeTools(),
    )

    with TestClient(app) as client:
        assert validator.warmup_started.wait(timeout=1)
        assert client.get("/health").status_code == 200
        validator.release_warmup.set()


def test_app_startup_skips_validator_warmup_when_disabled() -> None:
    class _WarmupValidator(StubPreSearchValidator):
        def __init__(self) -> None:
            self.warmup_calls = 0

        def warmup(self) -> None:
            self.warmup_calls += 1

    validator = _WarmupValidator()
    settings = Settings(
        LOG_LEVEL="INFO",
        APP_ENV="test",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
        LLM_WARMUP_ENABLED=False,
    )
    app = create_app(
        settings_override=settings,
        pre_search_validator_override=validator,
        tools_override=_FakeTools(),
    )

    with TestClient(app):
        pass

    assert validator.warmup_calls == 0


def test_catalog_result_count_boundary_and_utf8():
    class Tools:
        def __init__(self, count):
            self.count = count
        def search_parts(self, **kwargs):
            return [PartItem(item_id=f"RAD-{i}", title="Radiador de alum?nio", score=.8)
                    for i in range(self.count)]
    for count in (2, 5, 10, 11):
        app = create_app(
            settings_override=Settings(PRE_SEARCH_REVIEW_CAPTURE_ENABLED=False, LLM_WARMUP_ENABLED=False),
            pre_search_validator_override=StubPreSearchValidator(), tools_override=Tools(count),
        )
        with TestClient(app) as client:
            response = client.post('/respond', json=_payload('filtro de oleo ecosport 2008'))
        assert response.status_code == 200
        body = response.json()
        if count <= 10:
            assert body['actions'][0]['type'] == 'show_items'
            assert len(body['actions'][0]['items']) == count
            assert 'alum?nio' in body['actions'][0]['items'][0]['title']
            assert body['conversation_state']['pending_slot'] is None
        else:
            assert body['conversation_state']['pending_slot'] == 'result_disambiguation'
            assert body['actions'][0]['type'] == 'show_items'
            assert len(body['actions'][0]['items']) == 10
            assert body['actions'][1]['type'] == 'request_info'


def test_catalog_reply_reports_when_preferred_brand_is_absent():
    items = [PartItem(item_id="RAD-1", title="Radiador Cofap", score=.8)]

    text, action = ProcessAgentRequestUseCase._present_catalog_items(
        items, preferred_product_brand="Valeo",
    )

    assert 'marca preferida "Valeo"' in text
    assert action['type'] == 'show_items'


def test_refinement_to_ten_products_stops_asking():
    app = _make_app()
    with TestClient(app) as client:
        first = client.post('/respond', json=_payload('bandeja ecosport 2008')).json()
        second = client.post('/respond', json=_payload(
            'direito', conversation_state=first['conversation_state'],
        )).json()
    assert second['actions'][0]['type'] == 'show_items'
    assert len(second['actions'][0]['items']) == 10
    assert second['conversation_state']['pending_slot'] is None
