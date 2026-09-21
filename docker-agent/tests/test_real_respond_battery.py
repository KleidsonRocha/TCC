import json
from pathlib import Path

from scripts.eval import build_real_respond_battery_dataset as builder
from scripts.eval import run_real_respond_battery as runner


DATASET_PATH = Path("docs/assets/datasets/battery_structural_respond_v2.json")
REVIEW_PATH = Path("docs/assets/datasets/real_respond_battery_human_validation.md")


def test_battery_has_structural_scale_unique_ids_and_all_legacy_cases() -> None:
    document, scenarios = runner.load_scenarios(DATASET_PATH)

    assert document["schema_version"] == "2.0"
    assert len(scenarios) >= 120
    assert sum(len(item.turns) for item in scenarios) >= 160
    assert len({item.scenario_id for item in scenarios}) == len(scenarios)
    all_turns = [turn.turn_id for item in scenarios for turn in item.turns]
    assert len(set(all_turns)) == len(all_turns)
    legacy_ids = {case_id for item in scenarios for case_id in item.legacy_case_ids}
    assert legacy_ids == {f"case_{index:03d}" for index in range(1, 51)}


def test_battery_has_all_tiers_and_curated_human_review_metadata() -> None:
    _, scenarios = runner.load_scenarios(DATASET_PATH)

    assert {item.tier for item in scenarios} == {"smoke", "regression", "extended"}
    review = [item for item in scenarios if item.review_required]
    assert len(review) >= 20
    assert all(item.review_reason and item.validation_question for item in review)
    checklist = REVIEW_PATH.read_text(encoding="utf-8")
    assert all(item.scenario_id in checklist for item in review)


def test_tier_selection_is_cumulative() -> None:
    _, scenarios = runner.load_scenarios(DATASET_PATH)

    smoke = runner.select_scenarios(scenarios, "smoke", set(), set())
    regression = runner.select_scenarios(scenarios, "regression", set(), set())
    extended = runner.select_scenarios(scenarios, "extended", set(), set())

    assert {item.scenario_id for item in smoke} < {item.scenario_id for item in regression}
    assert {item.scenario_id for item in regression} < {item.scenario_id for item in extended}


def test_runner_builds_contracts_for_agent_and_comm() -> None:
    _, scenarios = runner.load_scenarios(DATASET_PATH)
    item = scenarios[0]
    current_turn = item.turns[0]
    history = [{"role": "user", "text": "anterior"}]
    state = {"pending_slot": "engine"}

    agent = runner.build_payload("agent", item, current_turn, "trace", history, state)
    comm = runner.build_payload("comm", item, current_turn, "trace", history, state)

    assert agent["context"] == {"last_messages": history, "conversation_state": state}
    assert agent["message"] == {"text": current_turn.message}
    assert comm == {
        "source": "eval",
        "conversation_id": f"eval-{item.scenario_id}",
        "text": current_turn.message,
        "branch_id": 1,
    }

    isolated = runner.build_payload(
        "comm", item, current_turn, "trace", history, state, "eval-unique-run-scenario"
    )
    assert isolated["conversation_id"] == "eval-unique-run-scenario"


def test_runner_removes_current_and_future_turns_from_agent_context() -> None:
    _, scenarios = runner.load_scenarios(DATASET_PATH)
    item = scenarios[0]
    current_turn = item.turns[0]
    contaminated = [
        {"role": "user", "text": "anterior"},
        {"role": "assistant", "text": "resposta anterior"},
        {"role": "user", "text": current_turn.message},
        {"role": "assistant", "text": "resposta esperada contaminante"},
    ]

    payload = runner.build_payload(
        "agent", item, current_turn, "trace", contaminated, None
    )

    assert payload["context"]["last_messages"] == contaminated[:2]


def test_runner_normalizes_agent_contract_and_evaluates_rich_assertions() -> None:
    body = {
        "reply": {"text": "Qual a motorizacao?"},
        "actions": [{"type": "request_info"}],
        "handoff": {"required": False},
        "tool_trace": {"used_tools": ["pre_search_deterministic_ask"], "pre_search_path": "deterministic_ask"},
        "conversation_state": {
            "criteria": {"part_query": "radiador", "part_code": None},
            "items": [{"part_query": "radiador", "vehicle_model": "Gol"}],
            "pending_slot": "engine",
        },
    }
    normalized = runner.normalize_response(body)
    failures = runner.evaluate_expectations({
        "status": 200,
        "reply_contains": ["motorizacao"],
        "action_type": "request_info",
        "question_key": "engine",
        "question_key_excludes": ["side", "axle"],
        "pre_search_path": "deterministic_ask",
        "used_tools_contains": ["pre_search_deterministic_ask"],
        "criteria_contains": {"part_query": "radiador"},
        "items_contains": [{"part_query": "radiador", "vehicle_model": "Gol"}],
        "part_code": None,
        "handoff_required": False,
    }, 200, normalized, "agent")

    assert failures == []


def test_runner_extracts_ranked_candidates_from_show_items_action() -> None:
    normalized = runner.normalize_response({
        "reply": {"text": "Encontrei opcoes."},
        "actions": [{
            "type": "show_items",
            "items": [
                {"item_id": "A-1", "title": "Primeira peca", "score": 0.82},
                {"item_id": "B-2", "title": "Segunda peca", "score": 0.74},
            ],
        }],
    })

    assert normalized["catalog_candidates"] == [
        {"position": 1, "item_id": "A-1", "title": "Primeira peca", "score": 0.82},
        {"position": 2, "item_id": "B-2", "title": "Segunda peca", "score": 0.74},
    ]


def test_runner_reports_assertion_failures_without_hiding_them() -> None:
    normalized = runner.normalize_response({
        "reply": {"text": "Qual lado?"},
        "actions": [],
        "handoff": {"required": False},
        "tool_trace": {"used_tools": [], "pre_search_path": "llm"},
        "conversation_state": {"criteria": {}, "pending_slot": "side"},
    })

    failures = runner.evaluate_expectations(
        {"status": 200, "question_key_excludes": ["side"], "pre_search_path": "deterministic_ask"},
        200,
        normalized,
        "agent",
    )

    assert "question_key_excludes: 'side' found" in failures
    assert any(item.startswith("pre_search_path:") for item in failures)


def test_builder_is_reproducible_and_matches_versioned_dataset() -> None:
    built = builder.build_document()
    versioned = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    assert built == versioned


def test_default_output_is_unique_and_outside_versioned_reports() -> None:
    first = runner.default_output_paths("agent")
    second = runner.default_output_paths("agent")

    assert first != second
    assert all(str(path).replace("\\", "/").startswith(".tmp/eval/") for path in first + second)
