"""Rebalance a pre-search dataset without splitting conversations."""

import argparse
import hashlib
import re
from collections import defaultdict
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.config import Settings
from app.infra.postgres_conninfo import build_catalog_conninfo


_CAPTURE_KEY = re.compile(r"^review_capture_(\d+)_")


def _group_key(example_key: str, conversation_by_interaction: dict[int, str]) -> str:
    match = _CAPTURE_KEY.match(example_key)
    if match:
        interaction_id = int(match.group(1))
        conversation_id = conversation_by_interaction.get(interaction_id)
        if conversation_id:
            return f"conversation:{conversation_id}"
    return f"example:{example_key}"


def _targets(total: int) -> dict[str, int]:
    validation = round(total * 0.10)
    test = round(total * 0.10)
    return {"train": total - validation - test, "validation": validation, "test": test}


def rebalance(*, settings: Settings, dataset_slug: str) -> dict[str, Any]:
    with psycopg.connect(build_catalog_conninfo(settings), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM pre_search_fine_tuning_dataset_header WHERE slug=%s AND is_active",
                (dataset_slug,),
            )
            header = cur.fetchone()
            if not header:
                raise RuntimeError(f"Dataset nao encontrado: {dataset_slug}")
            dataset_id = int(header["id"])

            cur.execute(
                """
                SELECT id, example_key, data_split
                FROM pre_search_fine_tuning_dataset_record
                WHERE dataset_id=%s AND is_active AND include_in_fine_tune
                ORDER BY example_key
                """,
                (dataset_id,),
            )
            records = [dict(row) for row in cur.fetchall()]
            if not records:
                raise RuntimeError("Dataset sem registros ativos")

            interaction_ids = []
            for row in records:
                match = _CAPTURE_KEY.match(str(row["example_key"]))
                if match:
                    interaction_ids.append(int(match.group(1)))
            conversation_by_interaction: dict[int, str] = {}
            if interaction_ids:
                cur.execute(
                    "SELECT id, conversation_id FROM pre_search_review_interaction WHERE id = ANY(%s)",
                    (interaction_ids,),
                )
                conversation_by_interaction = {
                    int(row["id"]): str(row["conversation_id"])
                    for row in cur.fetchall()
                    if row.get("conversation_id")
                }

            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in records:
                groups[_group_key(str(row["example_key"]), conversation_by_interaction)].append(row)

            targets = _targets(len(records))
            counts = {split: 0 for split in targets}
            assignments: dict[int, str] = {}
            ordered_groups = sorted(
                groups.items(),
                key=lambda item: (-len(item[1]), hashlib.sha256(item[0].encode("utf-8")).hexdigest()),
            )
            for group_name, rows in ordered_groups:
                size = len(rows)
                split = min(
                    targets,
                    key=lambda candidate: (
                        max(0, counts[candidate] + size - targets[candidate]),
                        abs((counts[candidate] + size) - targets[candidate]),
                        candidate,
                    ),
                )
                counts[split] += size
                for row in rows:
                    assignments[int(row["id"])] = split

            for record_id, split in assignments.items():
                cur.execute(
                    "UPDATE pre_search_fine_tuning_dataset_record SET data_split=%s, updated_by=%s, updated_at=NOW() WHERE id=%s",
                    (split, "dataset_rebalance", record_id),
                )
        conn.commit()

    return {"dataset_slug": dataset_slug, "targets": targets, "assigned": counts, "groups": len(groups)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-slug", default="pre-search-ft-v1")
    args = parser.parse_args()
    print(rebalance(settings=Settings(), dataset_slug=args.dataset_slug))


if __name__ == "__main__":
    main()
