from typing import Any, Protocol

from app.core.domain.models import ConversationState
from app.core.domain.pre_search import PreSearchValidation, SearchCriteria


class PreSearchValidatorPort(Protocol):
    def validate_item_for_search(
        self,
        criteria: SearchCriteria,
        *,
        message_text: str,
        last_messages: list[dict[str, Any]] | None = None,
    ) -> PreSearchValidation:
        raise NotImplementedError

    def try_validate_deterministic_ask(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
        conversation_state: ConversationState | None = None,
    ) -> PreSearchValidation | None:
        raise NotImplementedError

    def validate(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
        conversation_state: ConversationState | None = None,
    ) -> PreSearchValidation:
        raise NotImplementedError
