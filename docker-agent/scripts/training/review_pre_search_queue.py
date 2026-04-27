import argparse
import json
import re
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings
from app.infra.postgres_conninfo import build_catalog_conninfo


def _json_value(raw: str | None, *, default: Any) -> Any:
    if raw is None or not str(raw).strip():
        return default
    return json.loads(raw)


def _normalize_example_key(raw: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", raw.strip().lower()).strip("_")
    return sanitized or "review_capture"


def list_queue(*, settings: Settings, status: str, limit: int) -> None:
    with psycopg.connect(build_catalog_conninfo(settings), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    created_at,
                    trace_id,
                    conversation_id,
                    branch_id,
                    message_text,
                    predicted_decision,
                    predicted_confidence,
                    predicted_missing_fields,
                    predicted_next_question,
                    final_handoff_required,
                    llm_model,
                    llm_endpoint_used,
                    llm_output_valid,
                    llm_fallback_used,
                    llm_decision_raw,
                    review_status,
                    review_priority_score,
                    reviewed_decision,
                    reviewed_question_key,
                    reviewed_question_prompt
                FROM pre_search_review_queue
                WHERE review_status = %s
                ORDER BY review_priority_score DESC, created_at ASC
                LIMIT %s
                """,
                (status, limit),
            )
            rows = [dict(row) for row in cur.fetchall()]

    print(json.dumps({"status": status, "count": len(rows), "items": rows}, ensure_ascii=False, indent=2, default=str))


def review_case(
    *,
    settings: Settings,
    interaction_id: int,
    decision: str,
    reviewed_by: str | None,
    reviewed_notes: str | None,
    criteria_json: str | None,
    missing_fields_json: str | None,
    question_key: str | None,
    question_prompt: str | None,
    question_options_json: str | None,
) -> None:
    reviewed_criteria = _json_value(criteria_json, default=None)
    reviewed_missing_fields = _json_value(missing_fields_json, default=None)
    reviewed_question_options = _json_value(question_options_json, default=None)

    if decision == "ask" and (not question_key or not question_prompt):
        raise ValueError("Para decision=ask informe --question-key e --question-prompt.")

    with psycopg.connect(build_catalog_conninfo(settings), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pre_search_review_interaction
                SET
                    review_status = 'reviewed',
                    reviewed_decision = %s,
                    reviewed_criteria = COALESCE(%s, reviewed_criteria),
                    reviewed_missing_fields = COALESCE(%s, reviewed_missing_fields),
                    reviewed_question_key = %s,
                    reviewed_question_prompt = %s,
                    reviewed_question_options = %s,
                    reviewed_notes = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, review_status, reviewed_decision, reviewed_question_key, reviewed_question_prompt
                """,
                (
                    decision,
                    Jsonb(reviewed_criteria) if reviewed_criteria is not None else None,
                    Jsonb(reviewed_missing_fields) if reviewed_missing_fields is not None else None,
                    question_key,
                    question_prompt,
                    Jsonb(reviewed_question_options) if reviewed_question_options is not None else None,
                    reviewed_notes,
                    reviewed_by,
                    interaction_id,
                ),
            )
            row = cur.fetchone()
        conn.commit()

    if not row:
        raise RuntimeError(f"Interacao nao encontrada: {interaction_id}")

    print(json.dumps({"updated": dict(row)}, ensure_ascii=False, indent=2))


def promote_cases(
    *,
    settings: Settings,
    dataset_slug: str,
    data_split: str,
    interaction_id: int | None,
    limit: int,
    reviewed_by: str | None,
) -> None:
    promoted: list[dict[str, Any]] = []
    with psycopg.connect(build_catalog_conninfo(settings), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM pre_search_fine_tuning_dataset_header WHERE slug = %s",
                (dataset_slug,),
            )
            dataset_row = cur.fetchone()
            if not dataset_row:
                raise RuntimeError(f"Dataset de fine-tuning nao encontrado: {dataset_slug}")
            dataset_id = int(dataset_row["id"])

            if interaction_id is not None:
                cur.execute(
                    """
                    SELECT *
                    FROM pre_search_review_interaction
                    WHERE id = %s
                      AND review_status = 'reviewed'
                    """,
                    (interaction_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT *
                    FROM pre_search_review_interaction
                    WHERE review_status = 'reviewed'
                    ORDER BY reviewed_at ASC NULLS LAST, created_at ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
            rows = [dict(row) for row in cur.fetchall()]

            for row in rows:
                reviewed_decision = str(row.get("reviewed_decision") or "").strip()
                if not reviewed_decision:
                    continue

                reviewed_criteria = row.get("reviewed_criteria") or row.get("predicted_criteria") or {}
                reviewed_missing_fields = row.get("reviewed_missing_fields") or row.get("predicted_missing_fields") or []
                next_question = None
                if reviewed_decision == "ask":
                    question_key = str(row.get("reviewed_question_key") or "").strip()
                    question_prompt = str(row.get("reviewed_question_prompt") or "").strip()
                    if not question_key or not question_prompt:
                        raise RuntimeError(
                            f"Interacao {row['id']} revisada como ask sem pergunta revisada."
                        )
                    next_question = {
                        "type": "request_info",
                        "key": question_key,
                        "prompt": question_prompt,
                        "options": row.get("reviewed_question_options"),
                    }

                example_key = f"review_capture_{row['id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                example_key = _normalize_example_key(example_key)
                notes = (
                    f"Capturado da fila de revisao. interaction_id={row['id']}. "
                    f"reviewed_by={reviewed_by or row.get('reviewed_by') or 'manual'}."
                )
                tags = ["review_capture", f"predicted_{row['predicted_decision']}"]

                cur.execute(
                    """
                    INSERT INTO pre_search_fine_tuning_dataset_record (
                        dataset_id,
                        example_key,
                        data_split,
                        input_message_text,
                        input_last_messages,
                        expected_decision,
                        expected_criteria,
                        expected_missing_fields,
                        expected_next_question,
                        expected_confidence,
                        part_code_source,
                        tags,
                        notes,
                        include_in_fine_tune,
                        is_active,
                        updated_by
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, TRUE, %s
                    )
                    """,
                    (
                        dataset_id,
                        example_key,
                        data_split,
                        row["message_text"],
                        Jsonb(row.get("last_messages") or []),
                        reviewed_decision,
                        Jsonb(reviewed_criteria),
                        Jsonb(reviewed_missing_fields),
                        Jsonb(next_question) if next_question is not None else None,
                        row.get("predicted_confidence") or 0.95,
                        "literal" if (reviewed_criteria or {}).get("part_code") else "none",
                        Jsonb(tags),
                        notes,
                        reviewed_by or row.get("reviewed_by") or "manual_review",
                    ),
                )

                cur.execute(
                    """
                    UPDATE pre_search_review_interaction
                    SET
                        review_status = 'promoted',
                        promoted_dataset_slug = %s,
                        promoted_example_key = %s,
                        promoted_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (dataset_slug, example_key, row["id"]),
                )
                promoted.append(
                    {
                        "interaction_id": row["id"],
                        "dataset_slug": dataset_slug,
                        "example_key": example_key,
                        "decision": reviewed_decision,
                    }
                )
        conn.commit()

    print(json.dumps({"promoted_count": len(promoted), "items": promoted}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerencia a fila de revisao de conversas do pre-search.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="Lista itens da fila de revisao.")
    list_parser.add_argument("--status", default="pending", choices=["pending", "reviewed"], help="Status a listar.")
    list_parser.add_argument("--limit", type=int, default=20, help="Quantidade maxima.")

    review_parser = subparsers.add_parser("review", help="Marca um item com a decisao correta.")
    review_parser.add_argument("--interaction-id", type=int, required=True, help="ID da interacao.")
    review_parser.add_argument("--decision", required=True, choices=["search", "ask", "handoff"])
    review_parser.add_argument("--criteria-json", default=None, help="JSON com criteria corrigido.")
    review_parser.add_argument("--missing-fields-json", default=None, help="JSON array com missing_fields corrigidos.")
    review_parser.add_argument("--question-key", default=None, help="Key da pergunta correta, se ask.")
    review_parser.add_argument("--question-prompt", default=None, help="Prompt da pergunta correta, se ask.")
    review_parser.add_argument("--question-options-json", default=None, help="JSON array com opcoes da pergunta.")
    review_parser.add_argument("--reviewed-by", default=None, help="Nome do revisor.")
    review_parser.add_argument("--notes", default=None, help="Observacoes da revisao.")

    promote_parser = subparsers.add_parser("promote", help="Promove itens revisados para o dataset de fine-tuning.")
    promote_parser.add_argument("--dataset-slug", default=None, help="Slug do dataset de fine-tuning.")
    promote_parser.add_argument("--split", default="train", choices=["train", "validation", "test"])
    promote_parser.add_argument("--interaction-id", type=int, default=None, help="Promove um unico item.")
    promote_parser.add_argument("--limit", type=int, default=20, help="Limite para promocao em lote.")
    promote_parser.add_argument("--reviewed-by", default=None, help="Nome do operador da promocao.")

    args = parser.parse_args()
    settings = Settings()

    if args.command == "list":
        list_queue(settings=settings, status=args.status, limit=args.limit)
        return

    if args.command == "review":
        review_case(
            settings=settings,
            interaction_id=args.interaction_id,
            decision=args.decision,
            reviewed_by=args.reviewed_by,
            reviewed_notes=args.notes,
            criteria_json=args.criteria_json,
            missing_fields_json=args.missing_fields_json,
            question_key=args.question_key,
            question_prompt=args.question_prompt,
            question_options_json=args.question_options_json,
        )
        return

    if args.command == "promote":
        promote_cases(
            settings=settings,
            dataset_slug=args.dataset_slug or settings.ft_dataset_slug,
            data_split=args.split,
            interaction_id=args.interaction_id,
            limit=args.limit,
            reviewed_by=args.reviewed_by,
        )


if __name__ == "__main__":
    main()
