"""Generate a safe review queue for model-to-manufacturer catalog links.

The source catalog contains independent lists of vehicle models and brands.
This script never infers a manufacturer: it lists only models absent from the
curated ``vehicle_model_brand.csv`` seed and ranks them by engine-record use.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


CSV_DIR = Path("db/init/csv")
MODELS_PATH = CSV_DIR / "vehicle_model.csv"
ENGINES_PATH = CSV_DIR / "engine_option.csv"
MAPPINGS_PATH = CSV_DIR / "vehicle_model_brand.csv"
DEFAULT_OUTPUT = Path(".tmp/catalog/model_brand_review.csv")


def normalize(value: str | None) -> str:
    raw = str(value or "").strip().casefold()
    decomposed = unicodedata.normalize("NFKD", raw)
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", without_marks).strip()


def is_catalog_model(value: str | None) -> bool:
    model = str(value or "").strip()
    return bool(model and model not in {"-", "--"} and not re.fullmatch(r"\(.*\)", model))


def load_models(path: Path) -> dict[str, str]:
    models: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            raw_model = str(row.get("veiculo") or "").strip()
            if not is_catalog_model(raw_model):
                continue
            normalized = normalize(raw_model)
            if not normalized:
                continue
            current = models.get(normalized)
            if current is None or (len(raw_model), raw_model) < (len(current), current):
                models[normalized] = raw_model
    return models


def load_mapped_models(path: Path) -> set[str]:
    with path.open(encoding="utf-8", newline="") as source:
        return {
            normalized
            for row in csv.DictReader(source)
            if (normalized := normalize(row.get("veiculo")))
        }


def load_engine_counts(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            raw_model = row.get("veiculo")
            if is_catalog_model(raw_model):
                counts[normalize(raw_model)] += 1
    return counts


def priority_for(engine_records: int) -> str:
    if engine_records >= 20:
        return "P1"
    if engine_records >= 5:
        return "P2"
    return "P3"


def build_rows(
    *,
    models_path: Path = MODELS_PATH,
    engines_path: Path = ENGINES_PATH,
    mappings_path: Path = MAPPINGS_PATH,
) -> list[dict[str, str | int]]:
    models = load_models(models_path)
    mapped_models = load_mapped_models(mappings_path)
    engine_counts = load_engine_counts(engines_path)
    priority_order = {"P1": 0, "P2": 1, "P3": 2}

    rows = [
        {
            "priority": priority_for(engine_counts[normalized]),
            "model_normalized": normalized,
            "model": model,
            "engine_records": engine_counts[normalized],
            "recommended_brand": "",
            "review_status": "pending",
        }
        for normalized, model in models.items()
        if normalized not in mapped_models
    ]
    return sorted(
        rows,
        key=lambda row: (
            priority_order[str(row["priority"])],
            -int(row["engine_records"]),
            str(row["model_normalized"]),
        ),
    )


def write_review(rows: list[dict[str, str | int]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "priority",
        "model_normalized",
        "model",
        "engine_records",
        "recommended_brand",
        "review_status",
    ]
    with output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows = build_rows()
    write_review(rows, args.output)
    counts = Counter(str(row["priority"]) for row in rows)
    print(
        json.dumps(
            {
                "output": args.output.as_posix(),
                "unmapped_models": len(rows),
                "priority_counts": dict(sorted(counts.items())),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
