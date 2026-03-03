from typing import Any

from pydantic import BaseModel, Field

from app.core.domain.models import HandoffInfo


class TestSendRequest(BaseModel):
    __test__ = False
    source: str | None = None
    conversation_id: str | None = None
    text: str
    branch_id: int | None = None


class TestSendResponse(BaseModel):
    __test__ = False
    conversation_id: str
    trace_id: str
    reply: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    handoff: HandoffInfo = Field(default_factory=HandoffInfo)
    confidence: float = 0.0
