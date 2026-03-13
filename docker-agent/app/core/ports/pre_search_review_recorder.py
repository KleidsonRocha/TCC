from typing import Any, Protocol


class PreSearchReviewRecorderPort(Protocol):
    def record_interaction(
        self,
        *,
        trace_id: str,
        conversation_id: str,
        branch_id: int,
        channel_name: str | None,
        schema_version: str,
        message_text: str,
        last_messages: list[dict[str, str]],
        predicted_decision: str,
        predicted_criteria: dict[str, Any],
        predicted_missing_fields: list[str],
        predicted_next_question: dict[str, Any] | None,
        predicted_confidence: float,
        final_reply_text: str,
        final_actions: list[dict[str, Any]],
        final_handoff_required: bool,
        final_handoff_reason: str | None,
        final_confidence: float,
        final_used_tools: list[str],
        final_latency_ms: float,
        search_query: str | None,
        llm_model: str,
        llm_num_predict: int,
        llm_endpoint_used: str | None = None,
        llm_raw_content: str | None = None,
        llm_output_valid: bool | None = None,
        llm_parse_error: str | None = None,
        llm_fallback_used: bool | None = None,
        llm_decision_raw: str | None = None,
    ) -> None:
        raise NotImplementedError
