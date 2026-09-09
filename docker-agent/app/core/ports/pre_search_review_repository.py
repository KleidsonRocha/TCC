from typing import Any, Protocol


class PreSearchReviewRepositoryPort(Protocol):
    def list_conversations(self, *, status: str, limit: int) -> list[dict[str, Any]]: ...

    def get_conversation(self, *, conversation_id: str) -> dict[str, Any] | None: ...

    def review_interaction(
        self,
        *,
        interaction_id: int,
        decision: str,
        criteria: dict[str, Any],
        items: list[dict[str, Any]] | None,
        missing_fields: list[str],
        question_key: str | None,
        question_prompt: str | None,
        question_options: list[str] | None,
        reviewed_notes: str | None,
        reviewed_by: str,
    ) -> dict[str, Any]: ...

    def discard_interaction(
        self, *, interaction_id: int, reviewed_notes: str | None, reviewed_by: str
    ) -> dict[str, Any]: ...

    def discard_pending_conversation(
        self, *, conversation_id: str, reviewed_notes: str | None, reviewed_by: str
    ) -> dict[str, Any]: ...

    def reopen_interaction(
        self, *, interaction_id: int, reviewed_notes: str | None, reviewed_by: str
    ) -> dict[str, Any]: ...
