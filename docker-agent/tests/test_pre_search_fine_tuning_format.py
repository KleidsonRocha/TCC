from app.infra.pre_search_fine_tuning_format import (
    build_fine_tuning_assistant_payload,
    build_fine_tuning_messages_record,
    build_fine_tuning_user_payload,
    normalize_context_messages,
)


def test_normalize_context_messages_discards_empty_entries() -> None:
    result = normalize_context_messages(
        [
            {"role": "user", "text": "radiador gol 2010"},
            {"role": "assistant", "text": "   "},
            {"text": "1.6"},
            "invalid",
        ]
    )
    assert result == [
        {"role": "user", "text": "radiador gol 2010"},
        {"role": "user", "text": "1.6"},
    ]


def test_build_fine_tuning_assistant_payload_keeps_contract_shape() -> None:
    result = build_fine_tuning_assistant_payload(
        decision="ask",
        criteria={"part_query": "radiador", "vehicle_model": "Gol", "vehicle_year": 2010},
        missing_fields=["engine"],
        next_question={
            "type": "request_info",
            "key": "engine",
            "prompt": "Qual a motorizacao do veiculo?",
            "options": ["1.0", "1.6", "Nao sei"],
        },
        confidence=0.96,
    )

    assert result == {
        "decision": "ask",
        "criteria": {
            "part_query": "radiador",
            "part_code": None,
            "vehicle_brand": None,
            "vehicle_model": "Gol",
            "vehicle_year": 2010,
            "engine": None,
            "side": None,
            "position": None,
            "axle": None,
            "variant": None,
            "quantity": None,
        },
        "missing_fields": ["engine"],
        "next_question": {
            "type": "request_info",
            "key": "engine",
            "prompt": "Qual a motorizacao do veiculo?",
            "options": ["1.0", "1.6", "Nao sei"],
        },
        "confidence": 0.96,
    }


def test_build_fine_tuning_messages_record_serializes_payloads() -> None:
    user_payload = build_fine_tuning_user_payload(
        message_text="AB-1234",
        last_messages=[],
        dictionary_seed_criteria={"part_code": "AB-1234"},
        score_policy={"part_code_bypass": True},
    )
    assistant_payload = build_fine_tuning_assistant_payload(
        decision="search",
        criteria={"part_code": "AB-1234"},
        missing_fields=[],
        next_question=None,
        confidence=0.99,
    )

    result = build_fine_tuning_messages_record(
        system_prompt="retorne json",
        user_payload=user_payload,
        assistant_payload=assistant_payload,
        metadata={"example_key": "search_explicit_part_code"},
    )

    assert result["messages"][0] == {"role": "system", "content": "retorne json"}
    assert '"message_text":"AB-1234"' in result["messages"][1]["content"]
    assert '"decision":"search"' in result["messages"][2]["content"]
    assert result["metadata"]["example_key"] == "search_explicit_part_code"
