from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.domain.models import HandoffInfo
from app.core.domain.response_stage import ConversationStage


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
    status: Literal["processing", "completed"] = "completed"
    stage: ConversationStage | None = None
    reply: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    items_text: str = ""
    handoff: HandoffInfo = Field(default_factory=HandoffInfo)
    confidence: float = 0.0
