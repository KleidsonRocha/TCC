import logging
from typing import Any

try:
    import psycopg
    from psycopg.types.json import Jsonb
except Exception:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]

from app.config import Settings
from app.core.ports.pre_search_review_recorder import PreSearchReviewRecorderPort
from app.infra.postgres_conninfo import build_catalog_conninfo


class NoOpPreSearchReviewRecorder(PreSearchReviewRecorderPort):
    def record_interaction(self, **_: Any) -> None:
        return None


class PGPreSearchReviewRecorder(PreSearchReviewRecorderPort):
    def __init__(self, *, settings: Settings, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

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
        if psycopg is None or Jsonb is None:
            raise RuntimeError("Driver psycopg indisponivel para gravar fila de revisao.")

        with psycopg.connect(build_catalog_conninfo(self._settings)) as conn:  # type: ignore[union-attr]
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO pre_search_review_interaction (
                        trace_id,
                        conversation_id,
                        branch_id,
                        channel_name,
                        schema_version,
                        message_text,
                        last_messages,
                        predicted_decision,
                        predicted_criteria,
                        predicted_missing_fields,
                        predicted_next_question,
                        predicted_confidence,
                        final_reply_text,
                        final_actions,
                        final_handoff_required,
                        final_handoff_reason,
                        final_confidence,
                        final_used_tools,
                        final_latency_ms,
                        search_query,
                        llm_model,
                        llm_num_predict,
                        llm_endpoint_used,
                        llm_raw_content,
                        llm_output_valid,
                        llm_parse_error,
                        llm_fallback_used,
                        llm_decision_raw,
                        review_priority_score
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        trace_id,
                        conversation_id,
                        branch_id,
                        channel_name,
                        schema_version,
                        message_text,
                        Jsonb(last_messages),
                        predicted_decision,
                        Jsonb(predicted_criteria),
                        Jsonb(predicted_missing_fields),
                        Jsonb(predicted_next_question) if predicted_next_question is not None else None,
                        round(float(predicted_confidence), 3),
                        final_reply_text,
                        Jsonb(final_actions),
                        bool(final_handoff_required),
                        final_handoff_reason,
                        round(float(final_confidence), 3),
                        Jsonb(final_used_tools),
                        round(float(final_latency_ms), 2),
                        search_query,
                        llm_model,
                        int(llm_num_predict),
                        llm_endpoint_used,
                        llm_raw_content,
                        llm_output_valid,
                        llm_parse_error,
                        llm_fallback_used,
                        llm_decision_raw,
                        self._priority_score(
                            predicted_decision=predicted_decision,
                            predicted_confidence=predicted_confidence,
                            final_handoff_required=final_handoff_required,
                            final_actions=final_actions,
                        ),
                    ),
                )
            conn.commit()

    @staticmethod
    def _priority_score(
        *,
        predicted_decision: str,
        predicted_confidence: float,
        final_handoff_required: bool,
        final_actions: list[dict[str, Any]],
    ) -> int:
        score = 0
        if final_handoff_required:
            score += 40
        if predicted_decision == "handoff":
            score += 30
        elif predicted_decision == "ask":
            score += 20
        if float(predicted_confidence) < 0.8:
            score += 20
        if final_actions:
            score += 10
        return score


def recorder_from_settings(*, settings: Settings, logger: logging.Logger) -> PreSearchReviewRecorderPort:
    if not settings.catalog_db_enabled or not settings.pre_search_review_capture_enabled:
        return NoOpPreSearchReviewRecorder()
    return PGPreSearchReviewRecorder(settings=settings, logger=logger)
