import csv
from pathlib import Path

from scripts.catalog.import_model_brand_review import merge_links, reviewed_links


def test_review_import_converts_local_brand_id_to_portable_name(tmp_path: Path) -> None:
    models = tmp_path / "vehicle_model.csv"
    brands = tmp_path / "vehicle_brand.csv"
    brand_ids = tmp_path / "brand_ids.csv"
    review = tmp_path / "review.csv"
    models.write_text("veiculo\nGOL\n", encoding="utf-8")
    brands.write_text("montadora\nVOLKSWAGEN\n", encoding="utf-8")
    brand_ids.write_text("id,name\n8,VOLKSWAGEN\n", encoding="utf-8")
    review.write_text(
        "model_normalized,model,recommended_brand\ngol,GOL,8\n",
        encoding="utf-8",
    )

    reviewed = reviewed_links(
        review_path=review,
        brand_ids_path=brand_ids,
        models_path=models,
        brands_path=brands,
    )
    merged = merge_links(existing={}, reviewed=reviewed)

    assert merged == [("GOL", "VOLKSWAGEN")]


def test_review_import_rejects_unknown_brand_id(tmp_path: Path) -> None:
    models = tmp_path / "vehicle_model.csv"
    brands = tmp_path / "vehicle_brand.csv"
    brand_ids = tmp_path / "brand_ids.csv"
    review = tmp_path / "review.csv"
    models.write_text("veiculo\nGOL\n", encoding="utf-8")
    brands.write_text("montadora\nVOLKSWAGEN\n", encoding="utf-8")
    brand_ids.write_text("id,name\n8,VOLKSWAGEN\n", encoding="utf-8")
    review.write_text(
        "model_normalized,model,recommended_brand\ngol,GOL,999\n",
        encoding="utf-8",
    )

    try:
        reviewed_links(
            review_path=review,
            brand_ids_path=brand_ids,
            models_path=models,
            brands_path=brands,
        )
    except ValueError as exc:
        assert "montadora desconhecida" in str(exc)
    else:
        raise AssertionError("ID de montadora desconhecido foi aceito")
