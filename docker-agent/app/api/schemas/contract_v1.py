from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.domain.models import ConversationState


class ChannelInfo(BaseModel):
    name: str | None = None


class MessagePayload(BaseModel):
    text: str


class ContextMessage(BaseModel):
    role: Literal["user", "assistant"] | str
    text: str


class ConversationContext(BaseModel):
    last_messages: list[ContextMessage] = Field(default_factory=list)
    conversation_state: ConversationState | None = None


class RuntimeInfo(BaseModel):
    locale: str | None = None
    timezone: str | None = None


class BusinessInfo(BaseModel):
    branch_id: int


class AgentRequestV1(BaseModel):
    schema_version: str
    trace_id: str
    conversation_id: str
    message: MessagePayload
    business: BusinessInfo
    channel: ChannelInfo | None = None
    context: ConversationContext | None = None
    runtime: RuntimeInfo | None = None


class ReplyPayload(BaseModel):
    text: str


class HandoffPayload(BaseModel):
    required: bool = False
    reason: str | None = None


class ToolTracePayload(BaseModel):
    used_tools: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0


class AgentResponseV1(BaseModel):
    schema_version: str = "1.0"
    trace_id: str
    conversation_id: str
    reply: ReplyPayload
    actions: list[dict[str, Any]] = Field(default_factory=list)
    handoff: HandoffPayload = Field(default_factory=HandoffPayload)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    tool_trace: ToolTracePayload
    conversation_state: ConversationState | None = None
