from typing import Literal

from pydantic import BaseModel, Field


PreSearchDecision = Literal["search", "ask", "handoff"]


class SearchCriteria(BaseModel):
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


class NextQuestion(BaseModel):
    type: Literal["request_info"] = "request_info"
    key: str
    prompt: str
    options: list[str] | None = None


class PreSearchValidation(BaseModel):
    decision: PreSearchDecision
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)
    missing_fields: list[str] = Field(default_factory=list)
    next_question: NextQuestion | None = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
