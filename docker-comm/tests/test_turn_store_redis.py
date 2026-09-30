import asyncio
import os
import threading
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis

from app.api.deps import get_process_inbound_message_use_case
from app.config import Settings
from app.core.domain.models import ProcessResult
from app.main import create_app
from app.infra.turn_store_redis import RedisTurnStore, turn_key


def test_turn_key_uses_current_message_and_normalized_identity() -> None:
    first = turn_key(
        source="whatsapp",
        conversation_id="whatsapp:room-1",
        branch_id=1,
        text="  Freio   Onix 2010 ",
    )
    same_message = turn_key(
        source="whatsapp",
        conversation_id="whatsapp:room-1",
        branch_id=1,
        text="freio onix 2010",
    )
    different_message = turn_key(
        source="whatsapp",
        conversation_id="whatsapp:room-1",
        branch_id=1,
        text="freio onix 2012",
    )
    assert first == same_message
    assert first != different_message


@pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="Requires the docker-comm Redis service",
)
def test_redis_turn_claim_result_and_expiration() -> None:
    async def scenario() -> None:
        redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
        store = RedisTurnStore(redis)
        key = f"turn:integration:{uuid4().hex}"
        try:
            assert await store.claim(key, "first", 5)
            assert not await store.claim(key, "second", 5)
            assert await store.get_owner(key) == "first"
            assert not await store.renew(key, "second", 5)
            assert await store.renew(key, "first", 5)
            assert not await store.finish(key, "second", {"http_status": 200}, 1)
            assert await store.finish(key, "first", {"http_status": 200}, 1)
            assert await store.get_owner(key) is None
            assert await store.get_result(key) == {"http_status": 200}
            await asyncio.sleep(1.1)
            assert await store.get_result(key) is None
            assert await store.claim(key, "third", 1)
            await asyncio.sleep(1.1)
            assert await store.get_owner(key) is None
            assert await store.claim(key, "fourth", 5)
        finally:
            await redis.delete(f"{key}:lock", f"{key}:result")
            await redis.aclose()

    asyncio.run(scenario())


@pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="Requires the docker-comm Redis service",
)
def test_http_retries_share_background_work_with_real_redis() -> None:
    class SlowUseCase:
        def __init__(self) -> None:
            self.release = threading.Event()
            self.calls = 0

        async def execute(self, **kwargs) -> ProcessResult:
            self.calls += 1
            await asyncio.to_thread(self.release.wait)
            return ProcessResult(
                conversation_id=kwargs["conversation_id"],
                trace_id=kwargs["trace_id"],
                reply="Resposta pronta",
                agent_status_code=200,
            )

    use_case = SlowUseCase()
    settings = Settings(
        AGENT_URL="http://agent.local/respond",
        REDIS_URL=os.environ["REDIS_URL"],
        TURN_WAIT_SECONDS=0.05,
        TURN_RESULT_TTL_SECONDS=2,
    )
    app = create_app(settings_override=settings)
    app.dependency_overrides[get_process_inbound_message_use_case] = lambda: use_case
    request = {
        "source": "whatsapp",
        "conversation_id": f"integration-{uuid4().hex}",
        "text": "Freio Onix 2010",
        "branch_id": 1,
    }

    with TestClient(app) as client:
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
            raise AssertionError("No completed response was stored")

        assert final.json()["reply"] == "Resposta pronta"
        assert final.json()["trace_id"] == first.json()["trace_id"]
        assert use_case.calls == 1
