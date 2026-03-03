import json

from redis.asyncio import Redis

from app.config import Settings
from app.core.domain.models import HistoryMessage
from app.core.ports.session_store import SessionStore


class RedisSessionStore(SessionStore):
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self._redis = redis
        self._settings = settings

    @classmethod
    def from_url(cls, redis_url: str, settings: Settings) -> "RedisSessionStore":
        redis = Redis.from_url(redis_url, decode_responses=True)
        return cls(redis=redis, settings=settings)

    def _history_key(self, conversation_id: str) -> str:
        return f"conv:{conversation_id}:history"

    async def get_messages(self, conversation_id: str) -> list[HistoryMessage]:
        raw_payload = await self._redis.get(self._history_key(conversation_id))
        if not raw_payload:
            return []
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        messages: list[HistoryMessage] = []
        for item in parsed:
            try:
                messages.append(HistoryMessage.model_validate(item))
            except Exception:
                continue
        return messages

    async def append_messages(
        self,
        conversation_id: str,
        messages: list[HistoryMessage],
        history_limit: int,
    ) -> None:
        current = await self.get_messages(conversation_id)
        merged = current + messages
        trimmed = merged[-history_limit:]
        serialized = json.dumps([message.model_dump() for message in trimmed], ensure_ascii=True)
        await self._redis.set(
            self._history_key(conversation_id),
            serialized,
            ex=self._settings.session_ttl_seconds,
        )

    async def close(self) -> None:
        await self._redis.aclose()

