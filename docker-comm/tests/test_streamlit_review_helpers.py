import pytest

from ui.streamlit_app import _build_review_criteria, _build_review_items, _optional_positive_int


def test_build_review_criteria_omits_blank_values_and_parses_numbers() -> None:
    result = _build_review_criteria({
        "part_query": " amortecedores suspensao ",
        "part_code": "",
        "vehicle_model": "PALIO",
        "vehicle_year": "2008",
        "position": "front",
        "quantity": "",
    })

    assert result == {
        "part_query": "amortecedores suspensao",
        "vehicle_model": "PALIO",
        "vehicle_year": 2008,
        "position": "front",
    }


@pytest.mark.parametrize("value", ["abc", "0", "-2"])
def test_optional_positive_int_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        _optional_positive_int(value, field_label="Quantidade")


def test_build_review_criteria_rejects_out_of_range_year_and_quantity() -> None:
    with pytest.raises(ValueError, match="Ano"):
        _build_review_criteria({"vehicle_year": "1800"})
    with pytest.raises(ValueError, match="Quantidade"):
        _build_review_criteria({"quantity": "1000"})


def test_build_review_items_preserves_individual_decisions() -> None:
    items = _build_review_items([
        {"decision": "search", "criteria": {"part_query": "coifa interna"}},
        {
            "decision": "ask",
            "criteria": {"part_query": "bucha da bandeja"},
            "missing_fields": ["side"],
            "question_key": "side",
            "question_prompt": "Qual lado?",
        },
    ])

    assert [item["decision"] for item in items] == ["search", "ask"]
    assert items[1]["missing_fields"] == ["side"]
