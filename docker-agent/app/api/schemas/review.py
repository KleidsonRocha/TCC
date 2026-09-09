from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.domain.pre_search import SearchCriteria


class ReviewItemSubmission(BaseModel):
    decision: Literal["search", "ask", "handoff"]
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)
    missing_fields: list[str] = Field(default_factory=list)
    question_key: str | None = None
    question_prompt: str | None = None
    question_options: list[str] | None = None

    @model_validator(mode="after")
    def validate_item(self) -> "ReviewItemSubmission":
        if not self.criteria.part_query and not self.criteria.part_code:
            raise ValueError("Cada item revisado exige part_query ou part_code.")
        if self.decision == "ask" and (
            not (self.question_key or "").strip()
            or not (self.question_prompt or "").strip()
            or not self.missing_fields
        ):
            raise ValueError("Um item revisado como ask exige campo faltante e pergunta.")
        if self.decision == "search" and self.missing_fields:
            raise ValueError("Um item pronto para busca nao pode ter campos faltantes.")
        return self


class ReviewSubmission(BaseModel):
    decision: Literal["search", "ask", "handoff"]
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)
    items: list[ReviewItemSubmission] | None = Field(default=None, max_length=20)
    missing_fields: list[str] = Field(default_factory=list)
    question_key: str | None = None
    question_prompt: str | None = None
    question_options: list[str] | None = None
    reviewed_notes: str | None = None
    reviewed_by: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_ask_question(self) -> "ReviewSubmission":
        if self.decision == "ask" and (
            not (self.question_key or "").strip()
            or not (self.question_prompt or "").strip()
        ):
            raise ValueError("Uma revisao ask exige question_key e question_prompt.")
        return self


class ReviewDiscardSubmission(BaseModel):
    reviewed_notes: str | None = None
    reviewed_by: str = Field(min_length=1, max_length=120)


class ReviewReopenSubmission(BaseModel):
    reviewed_notes: str | None = None
    reviewed_by: str = Field(min_length=1, max_length=120)
