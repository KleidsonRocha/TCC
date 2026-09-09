from typing import Any

from pydantic import BaseModel, Field

from app.core.domain.pre_search import SearchCriteria


class PartItem(BaseModel):
    item_id: str
    title: str
    score: float = Field(..., ge=0.0, le=1.0)
    attributes: dict[str, list[str]] = Field(default_factory=dict)


class ResultCandidateState(BaseModel):
    item_id: str
    title: str
    score: float = Field(..., ge=0.0, le=1.0)
    attributes: dict[str, list[str]] = Field(default_factory=dict)


class ResultDisambiguationOption(BaseModel):
    label: str
    candidate_ids: list[str] = Field(default_factory=list)


class ResultDisambiguationState(BaseModel):
    candidates: list[ResultCandidateState] = Field(default_factory=list)
    question_key: str
    prompt: str
    options: list[ResultDisambiguationOption] = Field(default_factory=list)
    asked_fields: list[str] = Field(default_factory=list)
    visible_candidate_ids: list[str] = Field(default_factory=list)
    attempt: int = Field(default=1, ge=1)
    max_attempts: int = Field(default=3, ge=1)


class HandoffInfo(BaseModel):
    required: bool = False
    reason: str | None = None


class ToolTrace(BaseModel):
    used_tools: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    stage_latency_ms: dict[str, float] = Field(default_factory=dict)
    pre_search_path: str | None = None


class ItemSearchResult(BaseModel):
    item: SearchCriteria
    status: str
    products: list[PartItem] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    error_message: str | None = None


class ConversationState(BaseModel):
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)
    # `criteria` remains the active/legacy item. `items` carries the complete
    # request when the customer mentions more than one part.
    items: list[SearchCriteria] | None = None
    pending_slot: str | None = None
    pending_question: str | None = None
    last_decision: str | None = None
    result_disambiguation: ResultDisambiguationState | None = None


class ProcessResult(BaseModel):
    reply_text: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    handoff: HandoffInfo = Field(default_factory=HandoffInfo)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    tool_trace: ToolTrace
    conversation_state: ConversationState | None = None
    item_results: list[ItemSearchResult] | None = None
