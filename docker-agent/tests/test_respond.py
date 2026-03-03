from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _make_app():
    settings = Settings(
        LOG_LEVEL="INFO",
        APP_ENV="test",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
    )
    return create_app(settings_override=settings)


def _payload(text: str, schema_version: str = "1.0") -> dict:
    return {
        "schema_version": schema_version,
        "trace_id": "trace-123",
        "conversation_id": "conv-001",
        "channel": {"name": "generic"},
        "message": {"text": text},
        "context": {"last_messages": []},
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
    assert body["actions"][0]["type"] == "request_info"
    assert body["tool_trace"]["used_tools"] == ["search_parts"]
    assert body["handoff"]["required"] is False


def test_respond_with_filtro_de_oleo_returns_single_match() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Quero filtro de oleo"))

    assert response.status_code == 200
    body = response.json()
    assert "codigo" in body["reply"]["text"]
    assert body["actions"] == []
    assert body["handoff"]["required"] is False


def test_respond_without_match_requests_handoff() -> None:
    app = _make_app()
    with TestClient(app) as client:
        response = client.post("/respond", json=_payload("Preciso de uma peca rara"))

    assert response.status_code == 200
    body = response.json()
    assert body["handoff"]["required"] is True
    assert body["handoff"]["reason"] == "no_match"


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
