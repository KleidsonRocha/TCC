import asyncio

from app.config import Settings
from app.core.domain.models import (
    ConversationState,
    ResultCandidateState,
    ResultDisambiguationOption,
    ResultDisambiguationState,
    SearchCriteriaState,
)
from app.infra.session_store_redis import RedisSessionStore


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int):
        _ = ex
        self.values[key] = value

    async def delete(self, key: str):
        self.values.pop(key, None)

    async def aclose(self):
        return None


def test_redis_store_round_trips_result_disambiguation_in_existing_state_key() -> None:
    redis = _FakeRedis()
    store = RedisSessionStore(
        redis=redis,  # type: ignore[arg-type]
        settings=Settings(
            AGENT_URL="http://agent.local/respond",
            REDIS_URL="redis://localhost:6379/0",
            SESSION_TTL_SECONDS=3600,
        ),
    )
    state = ConversationState(
        criteria=SearchCriteriaState(part_query="bandeja", vehicle_model="Ecosport"),
        pending_slot="result_disambiguation",
        pending_question="Qual lado corresponde?",
        last_decision="ask",
        result_disambiguation=ResultDisambiguationState(
            candidates=[
                ResultCandidateState(
                    item_id="BDJ-1",
                    title="Bandeja esquerda",
                    score=0.91,
                    attributes={"side": ["Esquerdo"]},
                )
            ],
            question_key="side",
            prompt="Qual lado corresponde?",
            options=[
                ResultDisambiguationOption(
                    label="Esquerdo",
                    candidate_ids=["BDJ-1"],
                )
            ],
            attempt=1,
        ),
    )

    asyncio.run(store.set_conversation_state("web:conv-1", state))
    restored = asyncio.run(store.get_conversation_state("web:conv-1"))

    assert set(redis.values) == {"conv:web:conv-1:state"}
    assert restored == state


def test_typed_refinements_round_trip_through_existing_redis_state():
    redis = _FakeRedis()
    store = RedisSessionStore(redis=redis,settings=Settings(
        AGENT_URL='http://agent.local/respond',REDIS_URL='redis://localhost:6379/0'))
    state = ConversationState(criteria=SearchCriteriaState(part_query='semi eixo',
        variant='LTZ 2.5 FLEX 4X4 CD AT',fuel='flex',transmission='automatico',abs=False))
    state.items=[SearchCriteriaState(part_query='radiador'),state.criteria]
    state.active_item_index=1
    state.item_results=[{'item':{'part_query':'radiador'},'status':'pending'}]
    asyncio.run(store.set_conversation_state('test:typed-refinements',state))
    restored=asyncio.run(store.get_conversation_state('test:typed-refinements'))
    assert restored==state
    assert restored.criteria.abs is False
    assert set(redis.values)=={'conv:test:typed-refinements:state'}
