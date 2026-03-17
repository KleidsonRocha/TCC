from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchCriteriaState(BaseModel):
    part_query: str | None = None
    part_code: str | None = None
    vehicle_brand: str | None = None
    vehicle_model: str | None = None
    vehicle_year: int | None = Field(default=None, ge=1900, le=2100)
    engine: str | None = None
    side: Literal["left", "right"] | None = None
    position: Literal["front", "rear"] | None = None
    axle: Literal["front", "rear"] | None = None
    variant: str | None = None
    quantity: int | None = Field(default=None, ge=1, le=999)


class ConversationState(BaseModel):
    criteria: SearchCriteriaState = Field(default_factory=SearchCriteriaState)
    pending_slot: str | None = None
    pending_question: str | None = None
    last_decision: str | None = None


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


class ProcessResult(BaseModel):
    conversation_id: str
    trace_id: str
    reply: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    handoff: HandoffInfo = Field(default_factory=HandoffInfo)
    confidence: float = 0.0
    agent_status_code: int
    conversation_state: ConversationState | None = None
