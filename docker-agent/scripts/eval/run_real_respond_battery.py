"""Run the versioned real-response battery without overwriting approved reports."""

from __future__ import annotations

import argparse
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_DATASET = Path("docs/assets/datasets/battery_real_omnichannel_250.json")
DEFAULT_OUTPUT_DIR = Path(".tmp/eval")
DEFAULT_API_URLS = {"agent": "http://localhost:8001/respond", "comm": "http://localhost:8000/test/send"}
TIER_RANK = {"smoke": 0, "regression": 1, "extended": 2}


@dataclass(frozen=True)
class Turn:
    turn_id: str
    message: str
    schema_version: str
    expect: dict[str, Any]
    human_response: str | None = None
    human_response_messages: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    category: str
    tier: str
    turns: tuple[Turn, ...]
    review_required: bool = False
    review_reason: str | None = None
    validation_question: str | None = None
    legacy_case_ids: tuple[str, ...] = ()
    human_response_consolidated: str | None = None
    human_response_messages: tuple[dict[str, Any], ...] = ()


def load_scenarios(path: Path) -> tuple[dict[str, Any], list[Scenario]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != "2.0":
        raise ValueError("dataset schema_version must be 2.0")
    scenarios: list[Scenario] = []
    scenario_ids: set[str] = set()
    turn_ids: set[str] = set()
    for raw in document.get("scenarios", []):
        scenario_id = str(raw["id"])
        if scenario_id in scenario_ids:
            raise ValueError(f"duplicate scenario id: {scenario_id}")
        scenario_ids.add(scenario_id)
        tier = str(raw["tier"])
        if tier not in TIER_RANK:
            raise ValueError(f"invalid tier in {scenario_id}: {tier}")
        turns: list[Turn] = []
        for raw_turn in raw.get("turns", []):
            turn_id = str(raw_turn["id"])
            if turn_id in turn_ids:
                raise ValueError(f"duplicate turn id: {turn_id}")
            turn_ids.add(turn_id)
            turns.append(Turn(
                turn_id,
                str(raw_turn["message"]),
                str(raw_turn.get("schema_version", "1.0")),
                dict(raw_turn.get("expect", {})),
                raw_turn.get("human_response"),
                tuple(raw_turn.get("human_response_messages", [])),
            ))
        if not turns:
            raise ValueError(f"scenario has no turns: {scenario_id}")
        scenarios.append(Scenario(
            scenario_id, str(raw["category"]), tier, tuple(turns),
            bool(raw.get("review_required", False)), raw.get("review_reason"),
            raw.get("validation_question"), tuple(raw.get("legacy_case_ids", [])),
            raw.get("human_response_consolidated"),
            tuple(raw.get("human_response_messages", [])),
        ))
    if not scenarios:
        raise ValueError("dataset has no scenarios")
    return document, scenarios


def select_scenarios(scenarios: Iterable[Scenario], tier: str, categories: set[str], scenario_ids: set[str]) -> list[Scenario]:
    return [item for item in scenarios if TIER_RANK[item.tier] <= TIER_RANK[tier]
            and (not categories or item.category in categories)
            and (not scenario_ids or item.scenario_id in scenario_ids)]


def build_payload(target: str, scenario: Scenario, turn: Turn, trace_id: str,
                  history: list[dict[str, str]], state: dict[str, Any] | None,
                  conversation_id: str | None = None) -> dict[str, Any]:
    resolved_conversation_id = conversation_id or f"eval-{scenario.scenario_id}"
    if target == "comm":
        return {"source": "eval", "conversation_id": resolved_conversation_id,
                "text": turn.message, "branch_id": 1}
    # Keep the evaluator safe when a caller supplies a captured context instead
    # of the incremental history built by main(). A current/future user turn
    # must never be sent as context for the turn being evaluated.
    history = history_before_turn(history, turn.message)
    return {
        "schema_version": turn.schema_version, "trace_id": trace_id,
        "conversation_id": resolved_conversation_id,
        "channel": {"name": "real-response-battery"}, "message": {"text": turn.message},
        "context": {"last_messages": history, "conversation_state": state},
        "runtime": {"locale": "pt-BR", "timezone": "America/Sao_Paulo"},
        "business": {"branch_id": 1},
    }


def history_before_turn(
    history: list[dict[str, str]],
    current_message: str,
) -> list[dict[str, str]]:
    """Return only messages strictly before the current user turn.

    Real conversation exports may contain the current turn and its answer. In
    that case, truncate at the current user message so the expected answer
    cannot leak into the request context.
    """
    for index, message in enumerate(history):
        if (
            str(message.get("role", "")).strip().lower() == "user"
            and str(message.get("text", "")) == current_message
        ):
            return [dict(item) for item in history[:index]]
    return [dict(item) for item in history]


def call_api(url: str, payload: dict[str, Any], timeout: float, api_key: str | None = None) -> tuple[int, Any, float]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    request = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode(),
                                     headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode()), round((time.perf_counter() - started) * 1000, 2)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw}
        return exc.code, body, round((time.perf_counter() - started) * 1000, 2)


def normalize_response(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        body = {}
    actions = body.get("actions") if isinstance(body.get("actions"), list) else []
    reply = body.get("reply")
    reply_text = reply.get("text", "") if isinstance(reply, dict) else reply or body.get("reply_text", "")
    handoff = body.get("handoff") if isinstance(body.get("handoff"), dict) else {}
    catalog_candidates = _catalog_candidates_from_actions(actions)
    return {
        "reply_text": str(reply_text), "actions": actions,
        "action_types": [item.get("type") for item in actions if isinstance(item, dict)],
        "catalog_candidates": catalog_candidates,
        "conversation_state": body.get("conversation_state") if isinstance(body.get("conversation_state"), dict) else {},
        "diagnostics": body.get("tool_trace") if isinstance(body.get("tool_trace"), dict) else {},
        "item_results": body.get("item_results") if isinstance(body.get("item_results"), list) else [],
        "handoff_required": bool(handoff.get("required", body.get("handoff_required", False))),
    }


def _catalog_candidates_from_actions(actions: list[Any]) -> list[dict[str, Any]]:
    """Preserve the ordered items exposed by `show_items` in either API path.

    The single-item agent flow intentionally uses `show_items` instead of
    `item_results`. The gateway forwards that action to the Streamlit UI, so an
    evaluator must read it as the source of candidate codes and scores.
    """
    candidates: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict) or action.get("type") != "show_items":
            continue
        items = action.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("item_id")
            if item_id is None:
                continue
            candidates.append(
                {
                    "position": len(candidates) + 1,
                    "item_id": str(item_id),
                    "title": str(item.get("title") or ""),
                    "score": item.get("score"),
                }
            )
    return candidates


def _values_match(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) or isinstance(expected, str):
        return str(actual or "").strip().casefold() == str(expected or "").strip().casefold()
    return actual == expected


def evaluate_expectations(expect: dict[str, Any], status: int, data: dict[str, Any], target: str) -> list[str]:
    failures: list[str] = []
    wanted = int(expect.get("status", 200))
    if status != wanted:
        return [f"status: expected {wanted}, got {status}"]
    if status != 200:
        return failures
    reply, actions = data["reply_text"].casefold(), data["action_types"]
    state, diag = data["conversation_state"], data["diagnostics"]
    criteria = state.get("criteria", {}) if isinstance(state.get("criteria"), dict) else {}

    def equal(key: str, actual: Any) -> None:
        if key in expect and actual != expect[key]:
            failures.append(f"{key}: expected {expect[key]!r}, got {actual!r}")

    equal("handoff_required", data["handoff_required"])
    for text in expect.get("reply_contains", []):
        if str(text).casefold() not in reply:
            failures.append(f"reply_contains: {text!r} not found")
    for text in expect.get("reply_excludes", []):
        if str(text).casefold() in reply:
            failures.append(f"reply_excludes: {text!r} was found")
    if "action_type" in expect and expect["action_type"] not in actions:
        failures.append(f"action_type: {expect['action_type']!r} not in {actions!r}")
    allowed = expect.get("action_type_one_of")
    if allowed and not any(item in allowed for item in actions):
        failures.append(f"action_type_one_of: none of {allowed!r} in {actions!r}")
    if target == "agent":
        equal("question_key", state.get("pending_slot"))
        equal("pending_slot", state.get("pending_slot"))
        equal("active_item_index", state.get("active_item_index"))
        if state.get("pending_slot") in expect.get("question_key_excludes", []):
            failures.append(f"question_key_excludes: {state.get('pending_slot')!r} found")
        equal("part_code", criteria.get("part_code"))
        equal("pre_search_path", diag.get("pre_search_path"))
        if expect.get("pre_search_path_one_of") and diag.get("pre_search_path") not in expect["pre_search_path_one_of"]:
            failures.append(f"pre_search_path_one_of: got {diag.get('pre_search_path')!r}")
        for key, value in expect.get("criteria_contains", {}).items():
            if not _values_match(criteria.get(key), value):
                failures.append(f"criteria_contains.{key}: expected {value!r}, got {criteria.get(key)!r}")
        expected_items = expect.get("items_contains")
        if expected_items is not None:
            actual_items = state.get("items", [])
            if not isinstance(actual_items, list):
                actual_items = []
            if len(actual_items) != len(expected_items):
                failures.append(
                    f"items_contains: expected {len(expected_items)} items, got {len(actual_items)}"
                )
            else:
                for index, expected_item in enumerate(expected_items):
                    actual_item = actual_items[index]
                    if not isinstance(actual_item, dict):
                        failures.append(f"items_contains[{index}]: expected object, got {actual_item!r}")
                        continue
                    for key, value in expected_item.items():
                        if not _values_match(actual_item.get(key), value):
                            failures.append(
                                f"items_contains[{index}].{key}: expected {value!r}, "
                                f"got {actual_item.get(key)!r}"
                            )
        expected_item_results = expect.get("item_results_contains")
        if expected_item_results is not None:
            actual_item_results = data["item_results"]
            if len(actual_item_results) != len(expected_item_results):
                failures.append(
                    "item_results_contains: expected "
                    f"{len(expected_item_results)} items, got {len(actual_item_results)}"
                )
            else:
                for index, expected_result in enumerate(expected_item_results):
                    actual_result = actual_item_results[index]
                    for key, value in expected_result.items():
                        if key == "item":
                            actual_item = actual_result.get("item", {})
                            for item_key, item_value in value.items():
                                if not _values_match(actual_item.get(item_key), item_value):
                                    failures.append(
                                        f"item_results_contains[{index}].item.{item_key}: "
                                        f"expected {item_value!r}, got {actual_item.get(item_key)!r}"
                                    )
                        elif not _values_match(actual_result.get(key), value):
                            failures.append(
                                f"item_results_contains[{index}].{key}: expected {value!r}, "
                                f"got {actual_result.get(key)!r}"
                            )
        tools = diag.get("used_tools", [])
        for tool in expect.get("used_tools_contains", []):
            if tool not in tools:
                failures.append(f"used_tools_contains: {tool!r} not in {tools!r}")
        for tool in expect.get("used_tools_excludes", []):
            if tool in tools:
                failures.append(f"used_tools_excludes: {tool!r} found")
        for tool, expected_count in expect.get("used_tools_count", {}).items():
            actual_count = tools.count(tool)
            if actual_count != expected_count:
                failures.append(
                    f"used_tools_count.{tool}: expected {expected_count}, got {actual_count}"
                )
        options = state.get("last_question_options", [])
        if "options_max" in expect and len(options) > int(expect["options_max"]):
            failures.append(f"options_max: expected <= {expect['options_max']}, got {len(options)}")
        for option in expect.get("options_contains", []):
            if option not in options:
                failures.append(f"options_contains: {option!r} not in {options!r}")
    return failures


def render_markdown(rows: list[dict[str, Any]], name: str) -> str:
    passed = sum(not row["assertion_failures"] for row in rows)
    lines = ["# Real response battery", "", f"Dataset: `{name}`.", "",
             f"Resultado: **{passed}/{len(rows)} turnos aprovados**.", "",
             "| cenário/turno | categoria | status | latência | resultado |",
             "|---|---|---:|---:|---|"]
    for row in rows:
        result = "PASS" if not row["assertion_failures"] else "FAIL: " + "; ".join(row["assertion_failures"])
        lines.append(f"| `{row['scenario_id']}/{row['turn_id']}` | {row['category']} | {row['status_code']} | {row['elapsed_ms']} ms | {result} |")
    return "\n".join(lines) + "\n"


def render_human_comparison(rows: list[dict[str, Any]], name: str) -> str:
    """Render a qualitative side-by-side report; human text is reference only."""
    referenced = [row for row in rows if row.get("human_reference")]
    lines = [
        "# Comparacao qualitativa: IA x vendedor",
        "",
        f"Dataset: `{name}`.",
        "",
        f"Turnos executados: **{len(rows)}**. Turnos com referencia humana: **{len(referenced)}**.",
        "",
        "> A resposta humana e uma referencia observacional. Ela pode incluir mensagens posteriores ao turno executado e nao e tratada automaticamente como gabarito semantico.",
        "",
        "| cenario/turno | resposta da IA | resposta/referencia humana | caminho |",
        "|---|---|---|---|",
    ]
    for row in referenced:
        ai = str(row.get("summary", {}).get("reply_text", "")).replace("|", "\\|").replace("\n", "<br>")
        human = str(row["human_reference"]).replace("|", "\\|").replace("\n", "<br>")
        path = row.get("summary", {}).get("diagnostics", {}).get("pre_search_path", "")
        lines.append(f"| `{row['scenario_id']}/{row['turn_id']}` | {ai} | {human} | `{path}` |")
    if not referenced:
        lines.extend(["", "Nenhuma referencia humana foi encontrada nos turnos selecionados."])
    return "\n".join(lines) + "\n"


def default_output_paths(target: str) -> tuple[Path, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    base = DEFAULT_OUTPUT_DIR / f"real_respond_battery_{target}_{stamp}"
    return base.with_suffix(".json"), base.with_suffix(".md")


def csv_set(values: list[str]) -> set[str]:
    return {item.strip() for value in values for item in value.split(",") if item.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--target", choices=sorted(DEFAULT_API_URLS), default="agent")
    parser.add_argument("--api-url")
    parser.add_argument("--api-key", help="optional X-API-Key used by docker-comm")
    parser.add_argument("--tier", choices=list(TIER_RANK), default="smoke")
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--scenario-id", action="append", default=[])
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--output-comparison-md", type=Path)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-fail-on-assertion", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    document, all_scenarios = load_scenarios(args.dataset)
    scenarios = select_scenarios(all_scenarios, args.tier, csv_set(args.category), csv_set(args.scenario_id))
    if not scenarios:
        print("No scenarios selected.", file=sys.stderr)
        return 2
    total = sum(len(item.turns) for item in scenarios)
    if args.list or args.dry_run:
        if args.list:
            for item in scenarios:
                print(f"{item.scenario_id}\t{item.tier}\t{item.category}\t{len(item.turns)}")
        print(json.dumps({"scenarios": len(scenarios), "turns": total, "tier": args.tier}))
        return 0

    output_json, output_md = default_output_paths(args.target)
    output_comparison_md = output_md.with_name(output_md.stem + "_human_comparison.md")
    output_json, output_md = args.output_json or output_json, args.output_md or output_md
    output_comparison_md = args.output_comparison_md or output_comparison_md
    rows: list[dict[str, Any]] = []
    api_url, sequence = args.api_url or DEFAULT_API_URLS[args.target], 0
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for scenario in scenarios:
        history: list[dict[str, str]] = []
        state: dict[str, Any] | None = None
        for turn in scenario.turns:
            sequence += 1
            trace_id = f"battery-{scenario.scenario_id}-{turn.turn_id}-{sequence}"
            conversation_id = f"eval-{run_id}-{scenario.scenario_id}"
            payload = build_payload(args.target, scenario, turn, trace_id, history, state, conversation_id)
            try:
                status, body, elapsed = call_api(api_url, payload, args.timeout, args.api_key)
                normalized = normalize_response(body)
                failures = evaluate_expectations(turn.expect, status, normalized, args.target)
            except (urllib.error.URLError, http.client.HTTPException, TimeoutError) as exc:
                status, body, elapsed = 0, {"error": str(exc)}, 0.0
                normalized, failures = normalize_response(body), [f"transport: {exc}"]
            human_reference = turn.human_response or scenario.human_response_consolidated
            rows.append({"scenario_id": scenario.scenario_id, "turn_id": turn.turn_id,
                         "category": scenario.category, "tier": scenario.tier,
                         "review_required": scenario.review_required,
                         "legacy_case_ids": list(scenario.legacy_case_ids), "request": payload,
                         "status_code": status, "elapsed_ms": elapsed, "response": body,
                         "summary": normalized, "assertion_failures": failures,
                         "human_reference": human_reference,
                         "human_response_messages": list(turn.human_response_messages or scenario.human_response_messages)})
            print(json.dumps({"progress": f"{sequence}/{total}", "scenario": scenario.scenario_id,
                              "turn": turn.turn_id, "status": status,
                              "result": "PASS" if not failures else "FAIL", "failures": failures}, ensure_ascii=False), flush=True)
            if status == 200 and args.target == "agent":
                history.extend([{"role": "user", "text": turn.message},
                                {"role": "assistant", "text": normalized["reply_text"]}])
                state = normalized["conversation_state"]
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_comparison_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(rows, str(document.get("name", "unknown"))), encoding="utf-8")
    output_comparison_md.write_text(
        render_human_comparison(rows, str(document.get("name", "unknown"))),
        encoding="utf-8",
    )
    failed = sum(bool(row["assertion_failures"]) for row in rows)
    print(json.dumps({"output_json": output_json.as_posix(), "output_md": output_md.as_posix(),
                      "output_comparison_md": output_comparison_md.as_posix(),
                      "turns": len(rows), "failed": failed}, ensure_ascii=False))
    return 1 if failed and not args.no_fail_on_assertion else 0


if __name__ == "__main__":
    sys.exit(main())
