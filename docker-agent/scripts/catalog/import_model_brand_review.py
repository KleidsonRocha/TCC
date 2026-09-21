"""Promote reviewed model-to-brand links into the portable bootstrap seed.

The human review queue may contain local ``pre_search_brand.id`` values.  This
tool converts them through a temporary ID→name export, validates every row
against the versioned catalog CSVs, and writes only portable brand names to
``vehicle_model_brand.csv``.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.catalog.generate_model_brand_review import (
    CSV_DIR,
    MODELS_PATH,
    load_models,
    normalize,
)


DEFAULT_REVIEW = Path(".tmp/catalog/model_brand_review_preenchido.csv")
DEFAULT_BRAND_IDS = Path(".tmp/catalog/pre_search_brand_ids.csv")
DEFAULT_OUTPUT = CSV_DIR / "vehicle_model_brand.csv"
BRANDS_PATH = CSV_DIR / "vehicle_brand.csv"


def load_brand_names(path: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            name = str(row.get("montadora") or "").strip()
            if name:
                names[normalize(name)] = name
    return names


def load_brand_ids(path: Path) -> dict[str, str]:
    # PowerShell's UTF-8 output can include a BOM.  Accept it because this
    # file is an operational bridge, never a versioned source of truth.
    with path.open(encoding="utf-8-sig", newline="") as source:
        return {
            str(row.get("id") or "").strip(): str(row.get("name") or "").strip()
            for row in csv.DictReader(source)
            if str(row.get("id") or "").strip() and str(row.get("name") or "").strip()
        }


def load_existing_links(path: Path) -> dict[str, tuple[str, str]]:
    links: dict[str, tuple[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            model = str(row.get("veiculo") or "").strip()
            brand = str(row.get("montadora") or "").strip()
            if model and brand:
                links[normalize(model)] = (model, brand)
    return links


def reviewed_links(
    *,
    review_path: Path,
    brand_ids_path: Path,
    models_path: Path = MODELS_PATH,
    brands_path: Path = BRANDS_PATH,
) -> dict[str, tuple[str, str]]:
    models = load_models(models_path)
    brands = load_brand_names(brands_path)
    brand_ids = load_brand_ids(brand_ids_path)
    links: dict[str, tuple[str, str]] = {}
    errors: list[str] = []

    with review_path.open(encoding="utf-8", newline="") as source:
        for row_number, row in enumerate(csv.DictReader(source), start=2):
            raw_brand = str(row.get("recommended_brand") or "").strip()
            if not raw_brand:
                continue
            model_key = normalize(row.get("model_normalized") or row.get("model"))
            if model_key not in models:
                errors.append(f"linha {row_number}: modelo desconhecido {model_key!r}")
                continue
            brand_name = brand_ids.get(raw_brand, raw_brand)
            brand = brands.get(normalize(brand_name))
            if not brand:
                errors.append(f"linha {row_number}: montadora desconhecida {raw_brand!r}")
                continue
            previous = links.get(model_key)
            if previous and normalize(previous[1]) != normalize(brand):
                errors.append(f"linha {row_number}: montadora conflitante para {models[model_key]!r}")
                continue
            links[model_key] = (models[model_key], brand)

    if errors:
        raise ValueError("Revisao nao pode ser importada:\n- " + "\n- ".join(errors[:30]))
    return links


def merge_links(
    *,
    existing: dict[str, tuple[str, str]],
    reviewed: dict[str, tuple[str, str]],
) -> list[tuple[str, str]]:
    merged = dict(existing)
    for model_key, reviewed_link in reviewed.items():
        existing_link = merged.get(model_key)
        if existing_link and normalize(existing_link[1]) != normalize(reviewed_link[1]):
            raise ValueError(
                f"Modelo {reviewed_link[0]!r} ja possui montadora "
                f"{existing_link[1]!r}; revise antes de substituir."
            )
        merged[model_key] = reviewed_link
    return sorted(merged.values(), key=lambda row: (normalize(row[0]), row[0]))


def write_links(rows: list[tuple[str, str]], output: Path) -> None:
    with output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=["veiculo", "montadora"])
        writer.writeheader()
        writer.writerows({"veiculo": model, "montadora": brand} for model, brand in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--brand-ids", type=Path, default=DEFAULT_BRAND_IDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    reviewed = reviewed_links(review_path=args.review, brand_ids_path=args.brand_ids)
    merged = merge_links(existing=load_existing_links(args.output), reviewed=reviewed)
    summary = {
        "reviewed_links": len(reviewed),
        "total_links": len(merged),
        "output": args.output.as_posix(),
        "applied": args.apply,
    }
    if args.apply:
        write_links(merged, args.output)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
