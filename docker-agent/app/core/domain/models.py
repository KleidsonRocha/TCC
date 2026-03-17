from typing import Any

from pydantic import BaseModel, Field

from app.core.domain.pre_search import SearchCriteria


class PartItem(BaseModel):
    item_id: str
    title: str
    score: float = Field(..., ge=0.0, le=1.0)


class HandoffInfo(BaseModel):
    required: bool = False
    reason: str | None = None


class ToolTrace(BaseModel):
    used_tools: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0


class ConversationState(BaseModel):
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)
    pending_slot: str | None = None
    pending_question: str | None = None
    last_decision: str | None = None


class ProcessResult(BaseModel):
    reply_text: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    handoff: HandoffInfo = Field(default_factory=HandoffInfo)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    tool_trace: ToolTrace
    conversation_state: ConversationState | None = None
