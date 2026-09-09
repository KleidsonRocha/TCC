import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.config import Settings
from app.infra.pre_search_catalog_pg import resolve_pre_search_catalog
from app.infra.pre_search_fine_tuning_format import (
    build_fine_tuning_assistant_payload,
    build_fine_tuning_messages_record,
    build_fine_tuning_user_payload,
    dumps_json,
    normalize_context_messages,
)
from app.infra.postgres_conninfo import build_catalog_conninfo
from app.infra.pre_search_validator_llm import LLMPreSearchValidator


def _build_settings(
    *,
    base: Settings,
    db_host: str | None,
    db_port: int | None,
    db_name: str | None,
    db_user: str | None,
    db_password: str | None,
) -> Settings:
    return Settings(
        APP_ENV=base.app_env,
        LOG_LEVEL=base.log_level,
        AGENT_PORT=base.agent_port,
        DEFAULT_LOCALE=base.default_locale,
        DEFAULT_TIMEZONE=base.default_timezone,
        CATALOG_DB_ENABLED=base.catalog_db_enabled,
        CATALOG_DB_HOST=db_host or base.catalog_db_host,
        CATALOG_DB_PORT=db_port or base.catalog_db_port,
        CATALOG_DB_NAME=db_name or base.catalog_db_name,
        CATALOG_DB_USER=db_user or base.catalog_db_user,
        CATALOG_DB_PASSWORD=db_password or base.catalog_db_password,
        CATALOG_DB_CONNECT_TIMEOUT_S=base.catalog_db_connect_timeout_s,
        LLM_BASE_URL=base.llm_base_url,
        LLM_MODEL=base.llm_model,
        LLM_TIMEOUT_MS=base.llm_timeout_ms,
        LLM_TEMPERATURE=base.llm_temperature,
        LLM_NUM_PREDICT=base.llm_num_predict,
        LLM_THINK=base.llm_think,
        LLM_LOG_RAW_RESPONSE=False,
        LLM_CATEGORIES_FILE=base.llm_categories_file,
    )
def _load_dataset(cur: psycopg.Cursor[Any], dataset_slug: str) -> dict[str, Any]:
    cur.execute(
        """
        SELECT
            id,
            slug,
            name,
            description,
            task_type,
            output_schema_version,
            base_model_hint,
            system_prompt_override
        FROM pre_search_fine_tuning_dataset_header
        WHERE slug = %s
          AND is_active
        """,
        (dataset_slug,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Dataset de fine-tuning nao encontrado: {dataset_slug}")
    return dict(row)


def _load_examples(cur: psycopg.Cursor[Any], dataset_slug: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            example_key,
            data_split,
            input_message_text,
            input_last_messages,
            expected_decision,
            expected_criteria,
            expected_items,
            expected_missing_fields,
            expected_next_question,
            expected_confidence,
            part_code_source,
            tags,
            notes
        FROM pre_search_fine_tuning_dataset_record_export
        WHERE dataset_slug = %s
        ORDER BY
            CASE data_split
                WHEN 'train' THEN 1
                WHEN 'validation' THEN 2
                ELSE 3
            END,
            example_key
        """,
        (dataset_slug,),
    )
    return [dict(row) for row in cur.fetchall()]


def _to_float(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0.0)


def _normalize_export_contract(
    *,
    decision: str,
    missing_fields: list[str],
    next_question: dict[str, Any] | None,
) -> tuple[list[str], dict[str, Any] | None, list[str]]:
    """Keep legacy promoted snapshots aligned with the current output contract.

    Older promoted records could retain a stale missing field after the review
    was corrected. A `search` target is complete by definition, so exporting
    that stale state would create contradictory supervision examples. The
    source record remains untouched; the normalization is recorded in metadata.
    """
    normalized_missing = list(missing_fields)
    normalized_question = next_question
    adjustments: list[str] = []
    if decision == "search" and (normalized_missing or normalized_question is not None):
        normalized_missing = []
        normalized_question = None
        adjustments.append("search_contract_cleared_stale_missing_fields")
    if decision != "ask" and normalized_question is not None:
        normalized_question = None
        adjustments.append("non_ask_contract_cleared_question")
    return normalized_missing, normalized_question, adjustments


def _build_validator(settings: Settings) -> LLMPreSearchValidator:
    catalog = resolve_pre_search_catalog(settings=settings, logger=_NullLogger())
    return LLMPreSearchValidator(settings=settings, logger=_NullLogger(), catalog=catalog)


def _pick_system_prompt(*, dataset_row: dict[str, Any], validator: LLMPreSearchValidator) -> str:
    prompt_override = str(dataset_row.get("system_prompt_override") or "").strip()
    if prompt_override:
        return prompt_override
    return validator.build_system_prompt()


def _build_export_rows(
    *,
    examples: list[dict[str, Any]],
    dataset_row: dict[str, Any],
    validator: LLMPreSearchValidator,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    system_prompt = _pick_system_prompt(dataset_row=dataset_row, validator=validator)

    for row in examples:
        last_messages = normalize_context_messages(row.get("input_last_messages"))
        message_text = str(row.get("input_message_text", "")).strip()
        dictionary_seed = validator.extract_dictionary_seed_criteria(
            message_text=message_text,
            last_messages=last_messages,
        )
        score_policy = validator.build_score_policy(dictionary_seed_criteria=dictionary_seed)
        user_payload = build_fine_tuning_user_payload(
            message_text=message_text,
            last_messages=last_messages,
            dictionary_seed_criteria=dictionary_seed.model_dump(exclude_none=True),
            score_policy=score_policy,
        )
        expected_decision = str(row.get("expected_decision", "")).strip()
        expected_missing_fields, expected_next_question, export_adjustments = _normalize_export_contract(
            decision=expected_decision,
            missing_fields=list(row.get("expected_missing_fields") or []),
            next_question=row.get("expected_next_question"),
        )
        assistant_payload = build_fine_tuning_assistant_payload(
            decision=expected_decision,
            criteria=row.get("expected_criteria") or {},
            items=[
                item.get("criteria") or {}
                for item in (row.get("expected_items") or [])
                if isinstance(item, dict)
                and (
                    (item.get("criteria") or {}).get("part_query")
                    or (item.get("criteria") or {}).get("part_code")
                )
            ] or None,
            missing_fields=expected_missing_fields,
            next_question=expected_next_question,
            confidence=_to_float(row.get("expected_confidence")),
        )
        metadata = {
            "dataset_slug": dataset_row["slug"],
            "example_key": row["example_key"],
            "data_split": row["data_split"],
            "part_code_source": row.get("part_code_source"),
            "tags": row.get("tags") or [],
            "notes": row.get("notes"),
            "item_reviews": row.get("expected_items") or [],
        }
        if export_adjustments:
            metadata["export_normalizations"] = export_adjustments
        messages_record = build_fine_tuning_messages_record(
            system_prompt=system_prompt,
            user_payload=user_payload,
            assistant_payload=assistant_payload,
            metadata=metadata,
        )
        canonical_record = {
            "metadata": metadata,
            "system_prompt": system_prompt,
            "user_payload": user_payload,
            "assistant_payload": assistant_payload,
        }
        grouped[str(row["data_split"])].append(
            {
                "messages": messages_record,
                "record": canonical_record,
            }
        )

    return grouped


def _write_split_files(*, output_dir: Path, split: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "messages_file": None, "records_file": None}

    messages_path = output_dir / f"{split}.messages.jsonl"
    records_path = output_dir / f"{split}.records.jsonl"

    messages_lines = [dumps_json(item["messages"]) for item in rows]
    records_lines = [dumps_json(item["record"]) for item in rows]

    messages_path.write_text("\n".join(messages_lines) + "\n", encoding="utf-8")
    records_path.write_text("\n".join(records_lines) + "\n", encoding="utf-8")

    return {
        "count": len(rows),
        "messages_file": str(messages_path),
        "records_file": str(records_path),
    }


def _write_manifest(
    *,
    output_dir: Path,
    dataset_row: dict[str, Any],
    system_prompt: str,
    split_files: dict[str, dict[str, Any]],
) -> Path:
    manifest = {
        "dataset_slug": dataset_row["slug"],
        "dataset_name": dataset_row["name"],
        "description": dataset_row.get("description"),
        "task_type": dataset_row.get("task_type"),
        "output_schema_version": dataset_row.get("output_schema_version"),
        "base_model_hint": dataset_row.get("base_model_hint"),
        "system_prompt_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
        "splits": split_files,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


class _NullLogger:
    def info(self, *args: Any, **kwargs: Any) -> None:
        return None

    def warning(self, *args: Any, **kwargs: Any) -> None:
        return None

    def exception(self, *args: Any, **kwargs: Any) -> None:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta dataset de fine-tuning do pre-search em JSONL.")
    parser.add_argument("--dataset-slug", default="pre-search-ft-v1", help="Slug do dataset salvo no Postgres.")
    parser.add_argument("--output-dir", default=".tmp/fine_tuning", help="Diretorio de saida para os assets.")
    parser.add_argument("--db-host", default=None, help="Host do Postgres.")
    parser.add_argument("--db-port", type=int, default=None, help="Porta do Postgres.")
    parser.add_argument("--db-name", default=None, help="Nome do banco.")
    parser.add_argument("--db-user", default=None, help="Usuario do banco.")
    parser.add_argument("--db-password", default=None, help="Senha do banco.")
    args = parser.parse_args()

    base_settings = Settings()
    settings = _build_settings(
        base=base_settings,
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password,
    )
    validator = _build_validator(settings)

    with psycopg.connect(build_catalog_conninfo(settings), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            dataset_row = _load_dataset(cur, args.dataset_slug)
            examples = _load_examples(cur, args.dataset_slug)

    if not examples:
        raise RuntimeError(f"Dataset sem exemplos ativos para exportacao: {args.dataset_slug}")

    output_dir = Path(args.output_dir) / args.dataset_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped_rows = _build_export_rows(
        examples=examples,
        dataset_row=dataset_row,
        validator=validator,
    )
    system_prompt = _pick_system_prompt(dataset_row=dataset_row, validator=validator)
    system_prompt_path = output_dir / "system_prompt.txt"
    system_prompt_path.write_text(system_prompt + "\n", encoding="utf-8")

    split_files = {
        split: _write_split_files(output_dir=output_dir, split=split, rows=rows)
        for split, rows in grouped_rows.items()
    }
    manifest_path = _write_manifest(
        output_dir=output_dir,
        dataset_row=dataset_row,
        system_prompt=system_prompt,
        split_files=split_files,
    )

    print(
        json.dumps(
            {
                "dataset_slug": args.dataset_slug,
                "output_dir": str(output_dir),
                "system_prompt_file": str(system_prompt_path),
                "manifest_file": str(manifest_path),
                "splits": split_files,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
