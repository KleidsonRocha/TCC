from pathlib import Path

from scripts.catalog.generate_model_brand_review import build_rows, write_review


def test_model_brand_review_excludes_mapped_models_and_prioritizes_engine_use(
    tmp_path: Path,
) -> None:
    models = tmp_path / "vehicle_model.csv"
    engines = tmp_path / "engine_option.csv"
    mappings = tmp_path / "vehicle_model_brand.csv"
    models.write_text('veiculo\nGOL\nCORSA\nMAQUINA X\n', encoding="utf-8")
    engines.write_text(
        'veiculo,nome_motor\nCORSA,1.4\nCORSA,1.6\nMAQUINA X,DIESEL\n',
        encoding="utf-8",
    )
    mappings.write_text('veiculo,montadora\nGOL,VOLKSWAGEN\n', encoding="utf-8")

    rows = build_rows(
        models_path=models,
        engines_path=engines,
        mappings_path=mappings,
    )

    assert [row["model"] for row in rows] == ["CORSA", "MAQUINA X"]
    assert rows[0]["engine_records"] == 2
    assert rows[0]["review_status"] == "pending"

    output = tmp_path / "review.csv"
    write_review(rows, output)
    assert output.read_text(encoding="utf-8").startswith("priority,model_normalized")
