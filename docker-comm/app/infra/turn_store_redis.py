import hashlib
import json

from redis.asyncio import Redis


def turn_key(*, source: str, conversation_id: str, branch_id: int, text: str) -> str:
    normalized_text = " ".join(text.split()).casefold()
    identity = json.dumps(
        [source, conversation_id, branch_id, normalized_text],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"turn:{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"


class RedisTurnStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _lock_key(self, key: str) -> str:
        return f"{key}:lock"

    def _result_key(self, key: str) -> str:
        return f"{key}:result"

    def _trace_key(self, trace_id: str) -> str:
        return f"turn:trace:{trace_id}"

    async def bind_trace(
        self, trace_id: str, key: str, conversation_id: str, source: str, ttl_seconds: int
    ) -> None:
        await self._redis.set(
            self._trace_key(trace_id),
            json.dumps({"key": key, "conversation_id": conversation_id, "source": source}),
            ex=ttl_seconds,
        )

    async def get_trace(self, trace_id: str) -> dict | None:
        raw = await self._redis.get(self._trace_key(trace_id))
        return json.loads(raw) if raw is not None else None

    async def get_result(self, key: str) -> dict | None:
        raw = await self._redis.get(self._result_key(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def get_owner(self, key: str) -> str | None:
        return await self._redis.get(self._lock_key(key))

    async def claim(self, key: str, trace_id: str, lease_seconds: int) -> bool:
        return bool(
            await self._redis.set(
                self._lock_key(key), trace_id, ex=lease_seconds, nx=True
            )
        )

    async def renew(self, key: str, trace_id: str, lease_seconds: int) -> bool:
        return bool(
            await self._redis.eval(
                "if redis.call('GET', KEYS[1]) == ARGV[1] then "
                "return redis.call('EXPIRE', KEYS[1], ARGV[2]) else return 0 end",
                1,
                self._lock_key(key),
                trace_id,
                lease_seconds,
            )
        )

    async def finish(
        self,
        key: str,
        trace_id: str,
        result: dict,
        result_ttl_seconds: int,
    ) -> bool:
        serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        return bool(
            await self._redis.eval(
                "if redis.call('GET', KEYS[1]) == ARGV[1] then "
                "redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3]); "
                "redis.call('DEL', KEYS[1]); return 1 else return 0 end",
                2,
                self._lock_key(key),
                self._result_key(key),
                trace_id,
                serialized,
                result_ttl_seconds,
            )
        )

    async def release(self, key: str, trace_id: str) -> bool:
        return bool(
            await self._redis.eval(
                "if redis.call('GET', KEYS[1]) == ARGV[1] then "
                "return redis.call('DEL', KEYS[1]) else return 0 end",
                1,
                self._lock_key(key),
                trace_id,
            )
        )
