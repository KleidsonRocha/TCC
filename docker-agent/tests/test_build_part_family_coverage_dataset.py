from scripts.eval.build_part_family_coverage_dataset import build_documents


def test_part_family_coverage_dataset_covers_seeded_catalog_without_fake_llm_answers():
    coverage, llm_cases = build_documents()

    assert coverage["part_types_total"] == 338
    assert coverage["part_types_with_aliases"] > 300
    assert coverage["part_types_without_aliases"] == []
    assert coverage["aliases_total"] > 2_000
    assert len(coverage["cases"]) == coverage["aliases_total"] * 3 + len(coverage["part_types_without_aliases"]) * 3
    assert coverage["ambiguous_aliases_total"] > 0
    assert all(case["expected_part_families"] for case in coverage["cases"])
    disco = next(case for case in coverage["cases"] if case["message"] == "disco")
    assert disco["expected_part_families"] == ["discos de freio"]
    assert disco["ambiguous"] is False

    assert llm_cases
    assert all(case["expected"]["decision"] == "ask" for case in llm_cases)
    assert all(case["expected"]["missing_fields_contains"] == ["vehicle_model"] for case in llm_cases)
    assert all(case["expected"]["next_question_key"] == "vehicle_model" for case in llm_cases)
    assert len({case["expected"]["criteria"]["part_query"] for case in llm_cases}) == len(llm_cases)
