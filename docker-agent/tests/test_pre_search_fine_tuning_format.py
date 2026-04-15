from app.infra.pre_search_fine_tuning_format import (
    build_fine_tuning_assistant_payload,
    build_fine_tuning_messages_record,
    build_fine_tuning_user_payload,
    dumps_json,
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


def test_normalize_context_messages_trims_role_and_text_and_defaults_role() -> None:
    result = normalize_context_messages(
        [
            {"role": " assistant ", "text": "  preciso do ano  "},
            {"role": "   ", "text": "  Gol 2010  "},
            {"role": "user", "text": ""},
        ]
    )

    assert result == [
        {"role": "assistant", "text": "preciso do ano"},
        {"role": "user", "text": "Gol 2010"},
    ]


def test_build_fine_tuning_user_payload_normalizes_and_copies_inputs() -> None:
    last_messages = [
        {"role": " assistant ", "text": "  qual o motor?  "},
        {"text": " 1.6 "},
    ]
    dictionary_seed_criteria = {"part_code": "AB-1234"}
    score_policy = {"part_code_bypass": True}

    result = build_fine_tuning_user_payload(
        message_text="  AB-1234  ",
        last_messages=last_messages,
        dictionary_seed_criteria=dictionary_seed_criteria,
        score_policy=score_policy,
    )

    assert result == {
        "message_text": "AB-1234",
        "last_messages": [
            {"role": "assistant", "text": "qual o motor?"},
            {"role": "user", "text": "1.6"},
        ],
        "dictionary_seed_criteria": {"part_code": "AB-1234"},
        "score_policy": {"part_code_bypass": True},
    }
    assert result["dictionary_seed_criteria"] is not dictionary_seed_criteria
    assert result["score_policy"] is not score_policy


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


def test_build_fine_tuning_assistant_payload_for_search_keeps_null_next_question() -> None:
    result = build_fine_tuning_assistant_payload(
        decision="search",
        criteria={"part_code": "AB-1234", "quantity": 2},
        missing_fields=None,
        next_question=None,
        confidence=0.99,
    )

    assert result == {
        "decision": "search",
        "criteria": {
            "part_query": None,
            "part_code": "AB-1234",
            "vehicle_brand": None,
            "vehicle_model": None,
            "vehicle_year": None,
            "engine": None,
            "side": None,
            "position": None,
            "axle": None,
            "variant": None,
            "quantity": 2,
        },
        "missing_fields": [],
        "next_question": None,
        "confidence": 0.99,
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

    assert result == {
        "messages": [
            {"role": "system", "content": "retorne json"},
            {"role": "user", "content": dumps_json(user_payload)},
            {"role": "assistant", "content": dumps_json(assistant_payload)},
        ],
        "metadata": {"example_key": "search_explicit_part_code"},
    }


def test_dumps_json_uses_compact_non_ascii_serialization() -> None:
    payload = {"prompt": "ação", "options": ["1.0", "não sei"]}

    assert dumps_json(payload) == '{"prompt":"ação","options":["1.0","não sei"]}'
