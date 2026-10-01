import asyncio
import threading
import time

import httpx
from fastapi.testclient import TestClient

from app.api.deps import get_process_inbound_message_use_case
from app.config import Settings
from app.core.domain.models import HandoffInfo, ProcessResult
from app.main import create_app


class FakeTurnStore:
    def __init__(self) -> None:
        self.owners: dict[str, str] = {}
        self.results: dict[str, dict] = {}
        self.traces: dict[str, dict] = {}

    async def bind_trace(
        self, trace_id: str, key: str, conversation_id: str, source: str, ttl_seconds: int
    ) -> None:
        self.traces[trace_id] = {
            "key": key,
            "conversation_id": conversation_id,
            "source": source,
        }

    async def get_trace(self, trace_id: str) -> dict | None:
        return self.traces.get(trace_id)

    async def get_result(self, key: str) -> dict | None:
        return self.results.get(key)

    async def get_owner(self, key: str) -> str | None:
        return self.owners.get(key)

    async def claim(self, key: str, trace_id: str, lease_seconds: int) -> bool:
        if key in self.owners:
            return False
        self.owners[key] = trace_id
        return True

    async def renew(self, key: str, trace_id: str, lease_seconds: int) -> bool:
        return self.owners.get(key) == trace_id

    async def finish(self, key: str, trace_id: str, result: dict, result_ttl_seconds: int) -> bool:
        if self.owners.get(key) != trace_id:
            return False
        self.results[key] = result
        del self.owners[key]
        return True

    async def release(self, key: str, trace_id: str) -> bool:
        if self.owners.get(key) != trace_id:
            return False
        del self.owners[key]
        return True


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


def _make_app(enable_test_endpoint: bool = True, turn_wait_seconds: float = 35.0):
    FakeUseCase.last_call = None
    settings = Settings(
        AGENT_URL="http://agent.local/respond",
        REDIS_URL="redis://localhost:6379/0",
        ENABLE_TEST_ENDPOINT=enable_test_endpoint,
        TURN_WAIT_SECONDS=turn_wait_seconds,
    )
    app = create_app(settings_override=settings)
    app.dependency_overrides[get_process_inbound_message_use_case] = lambda: FakeUseCase()
    return app


def test_send_generates_conversation_id_when_missing() -> None:
    app = _make_app(enable_test_endpoint=True)
    with TestClient(app) as client:
        app.state.turn_store = FakeTurnStore()
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
        app.state.turn_store = FakeTurnStore()
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
        app.state.turn_store = FakeTurnStore()
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
        app.state.turn_store = FakeTurnStore()
        response = client.post("/test/send", json={"text": "Oi"})

    assert response.status_code == 404


def test_send_replays_completed_result_without_processing_twice() -> None:
    class CountingUseCase(FakeUseCase):
        calls = 0

        async def execute(self, **kwargs) -> ProcessResult:
            self.calls += 1
            return await super().execute(**kwargs)

    use_case = CountingUseCase()
    app = _make_app(turn_wait_seconds=1)
    app.dependency_overrides[get_process_inbound_message_use_case] = lambda: use_case
    request = {
        "source": "whatsapp",
        "conversation_id": "room-1",
        "text": "  Freio   Onix 2010  ",
        "branch_id": 1,
    }
    with TestClient(app) as client:
        app.state.turn_store = FakeTurnStore()
        first = client.post("/test/send", json=request)
        second = client.post(
            "/test/send", json={**request, "text": "freio onix 2010"}
        )

    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == "completed"
    assert first.json() == second.json()
    assert use_case.calls == 1


def test_send_repeated_while_processing_returns_same_job_then_result() -> None:
    class SlowUseCase(FakeUseCase):
        calls = 0

        def __init__(self) -> None:
            self.release = threading.Event()

        async def execute(self, **kwargs) -> ProcessResult:
            self.calls += 1
            await asyncio.to_thread(self.release.wait)
            return await super().execute(**kwargs)

    use_case = SlowUseCase()
    app = _make_app(turn_wait_seconds=0.05)
    app.dependency_overrides[get_process_inbound_message_use_case] = lambda: use_case
    request = {"source": "whatsapp", "conversation_id": "room-2", "text": "Bieleta"}
    with TestClient(app) as client:
        app.state.turn_store = FakeTurnStore()
        first = client.post("/test/send", json=request)
        second = client.post("/test/send", json=request)
        assert first.json()["status"] == second.json()["status"] == "processing"
        assert first.json()["trace_id"] == second.json()["trace_id"]
        assert use_case.calls == 1

        use_case.release.set()
        for _ in range(20):
            final = client.post("/test/send", json=request)
            if final.json()["status"] == "completed":
                break
            time.sleep(0.01)
        else:
            raise AssertionError("Background result was not stored")

    assert final.json()["reply"] == "Echo: Bieleta"
    assert final.json()["trace_id"] == first.json()["trace_id"]
    assert use_case.calls == 1


def test_send_worker_survives_caller_cancellation() -> None:
    class SlowUseCase(FakeUseCase):
        def __init__(self) -> None:
            self.started = asyncio.Event()
            self.release = asyncio.Event()
            self.calls = 0

        async def execute(self, **kwargs) -> ProcessResult:
            self.calls += 1
            self.started.set()
            await self.release.wait()
            return await super().execute(**kwargs)

    async def scenario() -> None:
        use_case = SlowUseCase()
        app = _make_app(turn_wait_seconds=1)
        app.dependency_overrides[get_process_inbound_message_use_case] = lambda: use_case
        async with app.router.lifespan_context(app):
            store = FakeTurnStore()
            app.state.turn_store = store
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                request = {"conversation_id": "room-3", "text": "Pastilha Onix"}
                caller = asyncio.create_task(client.post("/test/send", json=request))
                await asyncio.wait_for(use_case.started.wait(), timeout=1)
                caller.cancel()
                try:
                    await caller
                except asyncio.CancelledError:
                    pass
                use_case.release.set()
                for _ in range(20):
                    result = await client.post("/test/send", json=request)
                    if result.json()["status"] == "completed":
                        break
                    await asyncio.sleep(0.01)
                else:
                    raise AssertionError("Cancelled caller stopped the worker")
                assert result.json()["reply"] == "Echo: Pastilha Onix"
                assert use_case.calls == 1

    asyncio.run(scenario())


def test_pending_turn_can_restart_after_worker_shutdown() -> None:
    class NeverFinishesUseCase:
        async def execute(self, **kwargs) -> ProcessResult:
            _ = kwargs
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    store = FakeTurnStore()
    request = {"source": "whatsapp", "conversation_id": "room-restart", "text": "Freio"}
    first_app = _make_app(turn_wait_seconds=0.05)
    first_app.dependency_overrides[get_process_inbound_message_use_case] = lambda: NeverFinishesUseCase()
    with TestClient(first_app) as client:
        first_app.state.turn_store = store
        first = client.post("/test/send", json=request)
        assert first.json()["status"] == "processing"

    assert store.owners == {}
    second_app = _make_app(turn_wait_seconds=1)
    with TestClient(second_app) as client:
        second_app.state.turn_store = store
        second = client.post("/test/send", json=request)

    assert second.json()["status"] == "completed"
    assert second.json()["reply"] == "Echo: Freio"
