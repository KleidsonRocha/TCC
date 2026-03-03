from fastapi.testclient import TestClient

from app.api.deps import get_process_inbound_message_use_case
from app.config import Settings
from app.core.domain.models import HandoffInfo, ProcessResult
from app.main import create_app


class FakeUseCase:
    last_call: dict[str, str | int | None] | None = None

    async def execute(
        self,
        *,
        source: str,
        conversation_id: str,
        text: str,
        branch_id: int | None,
        trace_id: str,
    ) -> ProcessResult:
        FakeUseCase.last_call = {
            "source": source,
            "conversation_id": conversation_id,
            "text": text,
            "branch_id": branch_id,
            "trace_id": trace_id,
        }
        return ProcessResult(
            conversation_id=conversation_id,
            trace_id=trace_id,
            reply=f"Echo: {text}",
            actions=[],
            handoff=HandoffInfo(required=False, reason=None),
            confidence=0.9,
            agent_status_code=200,
        )


def _make_app(enable_test_endpoint: bool = True):
    FakeUseCase.last_call = None
    settings = Settings(
        AGENT_URL="http://agent.local/respond",
        REDIS_URL="redis://localhost:6379/0",
        ENABLE_TEST_ENDPOINT=enable_test_endpoint,
    )
    app = create_app(settings_override=settings)
    app.dependency_overrides[get_process_inbound_message_use_case] = lambda: FakeUseCase()
    return app


def test_send_generates_conversation_id_when_missing() -> None:
    app = _make_app(enable_test_endpoint=True)
    with TestClient(app) as client:
        response = client.post("/test/send", json={"text": "Oi"})

    assert response.status_code == 200
    body = response.json()
    assert "conversation_id" in body
    assert "trace_id" in body
    assert body["reply"] == "Echo: Oi"
    assert FakeUseCase.last_call is not None
    assert FakeUseCase.last_call["source"] == "generic"


def test_send_uses_source_to_namespace_internal_conversation_id() -> None:
    app = _make_app(enable_test_endpoint=True)
    with TestClient(app) as client:
        response = client.post(
            "/test/send",
            json={
                "source": "Whats App",
                "conversation_id": "conv-100",
                "text": "Oi",
            },
        )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == "conv-100"
    assert FakeUseCase.last_call is not None
    assert FakeUseCase.last_call["source"] == "whats-app"
    assert FakeUseCase.last_call["conversation_id"] == "whats-app:conv-100"


def test_send_replaces_blank_conversation_id() -> None:
    app = _make_app(enable_test_endpoint=True)
    with TestClient(app) as client:
        response = client.post(
            "/test/send",
            json={
                "source": "webchat",
                "conversation_id": "   ",
                "text": "Oi",
            },
        )

    assert response.status_code == 200
    generated_conversation_id = response.json()["conversation_id"]
    assert generated_conversation_id.strip() != ""
    assert FakeUseCase.last_call is not None
    assert FakeUseCase.last_call["conversation_id"] == f"webchat:{generated_conversation_id}"


def test_send_disabled_returns_404() -> None:
    app = _make_app(enable_test_endpoint=False)
    with TestClient(app) as client:
        response = client.post("/test/send", json={"text": "Oi"})

    assert response.status_code == 404
