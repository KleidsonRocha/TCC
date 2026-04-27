import json
from hashlib import sha256

from scripts.training.export_pre_search_fine_tuning_dataset import (
    _build_export_rows,
    _pick_system_prompt,
    _write_manifest,
    _write_split_files,
)


class _Seed:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self, exclude_none=True):
        _ = exclude_none
        return dict(self._payload)


class _Extractor:
    def extract(self, message_text: str, last_messages=None):
        _ = last_messages
        if "AB-1234" in message_text:
            return _Seed({"part_code": "AB-1234"})
        return _Seed({"part_query": "radiador", "vehicle_model": "Gol", "vehicle_year": 2010})


class _Validator:
    def build_score_policy(self, *, dictionary_seed_criteria):
        if hasattr(dictionary_seed_criteria, "model_dump"):
            serialized_seed = dictionary_seed_criteria.model_dump(exclude_none=True)
        else:
            serialized_seed = dict(dictionary_seed_criteria or {})
        return {
            "criteria_weights": {"part_query": 45, "part_code": 100},
            "min_score_to_search": 70,
            "seed": serialized_seed,
        }

    def build_system_prompt(self) -> str:
        return "prompt::categorias"

    def extract_dictionary_seed_criteria(self, *, message_text: str, last_messages=None):
        return _Extractor().extract(message_text, last_messages=last_messages)


def test_pick_system_prompt_prefers_override() -> None:
    validator = _Validator()

    result = _pick_system_prompt(
        dataset_row={"system_prompt_override": "retorne json estrito"},
        validator=validator,
    )

    assert result == "retorne json estrito"


def test_pick_system_prompt_falls_back_to_validator() -> None:
    validator = _Validator()

    result = _pick_system_prompt(
        dataset_row={"system_prompt_override": "   "},
        validator=validator,
    )

    assert result == "prompt::categorias"


def test_build_export_rows_groups_splits_and_serializes_records() -> None:
    validator = _Validator()
    dataset_row = {
        "slug": "pre-search-ft-v1",
        "system_prompt_override": "retorne json",
    }
    examples = [
        {
            "example_key": "ask_engine",
            "data_split": "train",
            "input_message_text": "radiador gol 2010",
            "input_last_messages": [],
            "expected_decision": "ask",
            "expected_criteria": {"part_query": "radiador", "vehicle_model": "Gol", "vehicle_year": 2010},
            "expected_missing_fields": ["engine"],
            "expected_next_question": {
                "type": "request_info",
                "key": "engine",
                "prompt": "Qual a motorizacao do veiculo?",
                "options": ["1.0", "1.6"],
            },
            "expected_confidence": 0.93,
            "part_code_source": "none",
            "tags": ["review_capture"],
            "notes": "pergunta de motor",
        },
        {
            "example_key": "search_part_code",
            "data_split": "validation",
            "input_message_text": "AB-1234",
            "input_last_messages": [],
            "expected_decision": "search",
            "expected_criteria": {"part_code": "AB-1234"},
            "expected_missing_fields": [],
            "expected_next_question": None,
            "expected_confidence": 0.99,
            "part_code_source": "literal",
            "tags": ["seed"],
            "notes": "codigo explicito",
        },
    ]

    grouped = _build_export_rows(
        examples=examples,
        dataset_row=dataset_row,
        validator=validator,
    )

    assert len(grouped["train"]) == 1
    assert len(grouped["validation"]) == 1
    assert grouped["test"] == []

    train_item = grouped["train"][0]
    assert train_item["record"]["metadata"]["dataset_slug"] == "pre-search-ft-v1"
    assert train_item["record"]["metadata"]["example_key"] == "ask_engine"
    assert train_item["record"]["assistant_payload"]["decision"] == "ask"
    assert train_item["messages"]["messages"][0] == {"role": "system", "content": "retorne json"}
    assert '"message_text":"radiador gol 2010"' in train_item["messages"]["messages"][1]["content"]
    assert '"decision":"ask"' in train_item["messages"]["messages"][2]["content"]

    validation_item = grouped["validation"][0]
    assert validation_item["record"]["assistant_payload"]["decision"] == "search"
    assert validation_item["record"]["metadata"]["part_code_source"] == "literal"


def test_write_split_files_returns_empty_descriptor_when_no_rows(tmp_path) -> None:
    result = _write_split_files(output_dir=tmp_path, split="train", rows=[])

    assert result == {"count": 0, "messages_file": None, "records_file": None}


def test_write_split_files_and_manifest_write_expected_files(tmp_path) -> None:
    rows = [
        {
            "messages": {
                "messages": [
                    {"role": "system", "content": "retorne json"},
                    {"role": "user", "content": '{"message_text":"AB-1234"}'},
                    {"role": "assistant", "content": '{"decision":"search"}'},
                ],
                "metadata": {"example_key": "search_part_code"},
            },
            "record": {
                "metadata": {"example_key": "search_part_code"},
                "system_prompt": "retorne json",
                "user_payload": {"message_text": "AB-1234"},
                "assistant_payload": {"decision": "search"},
            },
        }
    ]

    split_files = {
        "train": _write_split_files(output_dir=tmp_path, split="train", rows=rows),
        "validation": {"count": 0, "messages_file": None, "records_file": None},
        "test": {"count": 0, "messages_file": None, "records_file": None},
    }
    manifest_path = _write_manifest(
        output_dir=tmp_path,
        dataset_row={
            "slug": "pre-search-ft-v1",
            "name": "Dataset principal",
            "description": "dataset curado",
            "task_type": "pre_search_validation",
            "output_schema_version": "1.0",
            "base_model_hint": "Qwen/Qwen2.5-7B-Instruct",
        },
        system_prompt="retorne json",
        split_files=split_files,
    )

    train_messages_path = tmp_path / "train.messages.jsonl"
    train_records_path = tmp_path / "train.records.jsonl"

    assert train_messages_path.exists()
    assert train_records_path.exists()
    assert manifest_path.exists()

    messages_lines = train_messages_path.read_text(encoding="utf-8").strip().splitlines()
    records_lines = train_records_path.read_text(encoding="utf-8").strip().splitlines()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert len(messages_lines) == 1
    assert len(records_lines) == 1
    assert json.loads(records_lines[0])["assistant_payload"]["decision"] == "search"
    assert manifest["dataset_slug"] == "pre-search-ft-v1"
    assert manifest["splits"]["train"]["count"] == 1
    assert manifest["system_prompt_sha256"] == sha256("retorne json".encode("utf-8")).hexdigest()
