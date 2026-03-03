from typing import Any, Literal

from pydantic import BaseModel, Field


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


class ProcessResult(BaseModel):
    conversation_id: str
    trace_id: str
    reply: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    handoff: HandoffInfo = Field(default_factory=HandoffInfo)
    confidence: float = 0.0
    agent_status_code: int

