from typing import Any

from fastapi.testclient import TestClient

from app.config import Settings
from app.core.domain.review_errors import ReviewInteractionAlreadyEvaluatedError
from app.main import create_app


class _ReviewRepository:
    def __init__(self) -> None:
        self.review_calls: list[dict[str, Any]] = []
        self.discard_calls: list[dict[str, Any]] = []

    def list_conversations(self, *, status: str, limit: int) -> list[dict[str, Any]]:
        return [{
            "conversation_id": "webchat:conv-1",
            "interaction_count": 2,
            "pending_count": 1 if status == "pending" else 0,
            "reviewed_count": 1,
            "promoted_count": 0,
            "discarded_count": 0,
            "priority_score": 30,
            "latest_message": "dianteiro",
            "contains_llm": False,
        }][:limit]

    def get_conversation(self, *, conversation_id: str) -> dict[str, Any] | None:
        if conversation_id != "webchat:conv-1":
            return None
        return {
            "conversation_id": conversation_id,
            "interaction_count": 2,
            "pending_count": 1,
            "reviewed_count": 1,
            "promoted_count": 0,
            "discarded_count": 0,
            "conversation_completed": False,
            "interactions": [
                {"id": 1, "review_status": "reviewed", "message_text": "suspensao palio 2008"},
                {"id": 2, "review_status": "pending", "message_text": "dianteiro"},
            ],
        }

    def review_interaction(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs["interaction_id"] == 99:
            raise ReviewInteractionAlreadyEvaluatedError(interaction_id=99, review_status="reviewed")
        self.review_calls.append(kwargs)
        return {
            "interaction_id": kwargs["interaction_id"],
            "review_status": "reviewed",
            "pending_count": 0,
            "conversation_completed": True,
        }

    def discard_interaction(self, **kwargs: Any) -> dict[str, Any]:
        self.discard_calls.append(kwargs)
        return {"interaction_id": kwargs["interaction_id"], "review_status": "discarded", "pending_count": 0, "conversation_completed": True}

    def discard_pending_conversation(self, **kwargs: Any) -> dict[str, Any]:
        self.discard_calls.append(kwargs)
        return {"discarded_count": 2, "pending_count": 0, "conversation_completed": True}

    def reopen_interaction(self, **kwargs: Any) -> dict[str, Any]:
        self.review_calls.append(kwargs)
        return {"interaction_id": kwargs["interaction_id"], "review_status": "pending", "pending_count": 1, "conversation_completed": False}


def _app(repository: _ReviewRepository, *, api_key: str | None = None):
    settings = Settings(_env_file=None, APP_ENV="test", CATALOG_DB_ENABLED=False, REVIEW_API_KEY=api_key)
    return create_app(
        settings_override=settings,
        pre_search_validator_override=object(),
        tools_override=object(),
        review_repository_override=repository,
    )


def test_review_api_lists_and_loads_grouped_conversation() -> None:
    repository = _ReviewRepository()
    with TestClient(_app(repository)) as client:
        listing = client.get("/review/conversations", params={"status": "pending"})
        detail = client.get("/review/conversations/webchat%3Aconv-1")

    assert listing.status_code == 200
    assert listing.json()["items"][0]["pending_count"] == 1
    assert detail.status_code == 200
    assert [item["id"] for item in detail.json()["interactions"]] == [1, 2]


def test_review_api_saves_turn_and_reports_completed_conversation() -> None:
    repository = _ReviewRepository()
    payload = {
        "decision": "search",
        "criteria": {"part_query": "amortecedores suspensao", "vehicle_model": "PALIO", "vehicle_year": 2008, "position": "front"},
        "missing_fields": [],
        "reviewed_notes": "Fluxo correto",
        "reviewed_by": "Kleidson",
    }
    with TestClient(_app(repository)) as client:
        response = client.put("/review/interactions/2", json=payload)

    assert response.status_code == 200
    assert response.json()["conversation_completed"] is True
    assert repository.review_calls[0]["criteria"]["position"] == "front"


def test_review_api_accepts_multiple_items_with_individual_outcomes() -> None:
    repository = _ReviewRepository()
    payload = {
        "decision": "ask",
        "criteria": {"vehicle_model": "Hilux", "vehicle_year": 1997, "engine": "3.0"},
        "items": [
            {"decision": "search", "criteria": {"part_query": "coifa interna", "vehicle_model": "Hilux"}},
            {
                "decision": "ask",
                "criteria": {"part_query": "bucha da bandeja superior", "vehicle_model": "Hilux"},
                "missing_fields": ["side"],
                "question_key": "side",
                "question_prompt": "Qual o lado da bucha?",
            },
        ],
        "missing_fields": ["side"],
        "question_key": "side",
        "question_prompt": "Qual o lado da bucha?",
        "reviewed_by": "Kleidson",
    }
    with TestClient(_app(repository)) as client:
        response = client.put("/review/interactions/2", json=payload)

    assert response.status_code == 200
    assert len(repository.review_calls[0]["items"]) == 2
    assert repository.review_calls[0]["items"][1]["missing_fields"] == ["side"]


def test_review_api_requires_question_for_ask() -> None:
    repository = _ReviewRepository()
    with TestClient(_app(repository)) as client:
        response = client.put("/review/interactions/2", json={
            "decision": "ask", "criteria": {}, "missing_fields": ["engine"], "reviewed_by": "Kleidson"
        })

    assert response.status_code == 422
    assert repository.review_calls == []


def test_review_api_rejects_noncanonical_direction() -> None:
    repository = _ReviewRepository()
    with TestClient(_app(repository)) as client:
        response = client.put("/review/interactions/2", json={
            "decision": "search",
            "criteria": {"part_query": "bandeja", "side": "esquerdo"},
            "missing_fields": [],
            "reviewed_by": "Kleidson",
        })

    assert response.status_code == 422
    assert repository.review_calls == []


def test_review_api_reports_already_evaluated_turn() -> None:
    repository = _ReviewRepository()
    with TestClient(_app(repository)) as client:
        response = client.put("/review/interactions/99", json={
            "decision": "handoff", "criteria": {}, "missing_fields": [], "reviewed_by": "Kleidson"
        })

    assert response.status_code == 409
    assert "ja foi avaliada" in response.json()["detail"]


def test_review_api_discards_turn_and_complete_conversation() -> None:
    repository = _ReviewRepository()
    payload = {"reviewed_by": "Kleidson", "reviewed_notes": "Sem valor para treino"}
    with TestClient(_app(repository)) as client:
        turn = client.post("/review/interactions/2/discard", json=payload)
        conversation = client.post("/review/conversations/webchat%3Aconv-1/discard-pending", json=payload)

    assert turn.status_code == 200
    assert conversation.status_code == 200
    assert conversation.json()["discarded_count"] == 2


def test_review_api_key_is_optional_but_enforced_when_configured() -> None:
    repository = _ReviewRepository()
    with TestClient(_app(repository, api_key="secret")) as client:
        denied = client.get("/review/conversations")
        allowed = client.get("/review/conversations", headers={"X-Review-Key": "secret"})

    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_review_api_reopens_a_completed_turn() -> None:
    repository = _ReviewRepository()
    with TestClient(_app(repository)) as client:
        response = client.post("/review/interactions/1/reopen", json={
            "reviewed_by": "Kleidson", "reviewed_notes": "Corrigir marca"
        })

    assert response.status_code == 200
    assert response.json()["review_status"] == "pending"
