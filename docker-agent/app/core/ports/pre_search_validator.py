from typing import Any, Protocol

from app.core.domain.pre_search import PreSearchValidation


class PreSearchValidatorPort(Protocol):
    def validate(
        self,
        message_text: str,
        *,
        last_messages: list[dict[str, Any]] | None = None,
    ) -> PreSearchValidation:
        raise NotImplementedError
