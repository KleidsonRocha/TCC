from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchCriteriaState(BaseModel):
    part_query: str | None = None
    part_code: str | None = None
    preferred_product_brand: str | None = None
    vehicle_brand: str | None = None
    vehicle_model: str | None = None
    vehicle_year: int | None = Field(default=None, ge=1900, le=2100)
    engine: str | None = None
    side: Literal["left", "right"] | None = None
    position: Literal["front", "rear"] | None = None
    axle: Literal["front", "rear"] | None = None
    variant: str | None = None
    quantity: int | None = Field(default=None, ge=1, le=999)


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


class ConversationState(BaseModel):
    criteria: SearchCriteriaState = Field(default_factory=SearchCriteriaState)
    # Optional for backward compatibility; populated when a request contains
    # more than one independent part.
    items: list[SearchCriteriaState] | None = None
    pending_slot: str | None = None
    pending_question: str | None = None
    last_decision: str | None = None
    result_disambiguation: ResultDisambiguationState | None = None


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class ChannelInfo(BaseModel):
    name: str = "generic"
    message_id: str | None = None


class IncomingMessage(BaseModel):
    text: str


class ConversationContext(BaseModel):
    last_messages: list[HistoryMessage] = Field(default_factory=list)
    conversation_state: ConversationState | None = None


class RuntimeInfo(BaseModel):
    locale: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"


class BusinessInfo(BaseModel):
    branch_id: int


class AgentRequestPayload(BaseModel):
    schema_version: str = "1.0"
    trace_id: str
    conversation_id: str
    channel: ChannelInfo
    message: IncomingMessage
    context: ConversationContext
    runtime: RuntimeInfo
    business: BusinessInfo


class HandoffInfo(BaseModel):
    required: bool = False
    reason: str | None = None


class AgentResponsePayload(BaseModel):
    reply: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    handoff: HandoffInfo = Field(default_factory=HandoffInfo)
    confidence: float = 0.0
    conversation_state: ConversationState | None = None
    item_results: list[dict[str, Any]] | None = None


class ProcessResult(BaseModel):
    conversation_id: str
    trace_id: str
    reply: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    handoff: HandoffInfo = Field(default_factory=HandoffInfo)
    confidence: float = 0.0
    agent_status_code: int
    conversation_state: ConversationState | None = None
    item_results: list[dict[str, Any]] | None = None
