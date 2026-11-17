import json
import math
import statistics
from collections import Counter
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(math.floor((len(ordered) - 1) * fraction), len(ordered) - 1)
    return round(ordered[index], 2)


def observable(row: dict) -> dict:
    response = row.get("response") or {}
    actions = response.get("actions") or []
    state = response.get("conversation_state") or {}
    handoff = response.get("handoff") or {}
    action_types = [action.get("type") for action in actions]
    if row.get("status_code") != 200:
        outcome = "error"
    elif handoff.get("required"):
        outcome = "handoff"
    elif "request_info" in action_types:
        outcome = "ask"
    elif "show_items" in action_types or "search_parts" in row["summary"].get("used_tools", []):
        outcome = "search"
    else:
        outcome = "reply"
    request_info = next(
        (action for action in actions if action.get("type") == "request_info"),
        None,
    )
    return {
        "status_code": row.get("status_code"),
        "outcome": outcome,
        "handoff_required": handoff.get("required"),
        "handoff_reason": handoff.get("reason"),
        "action_types": action_types,
        "question_key": request_info.get("key") if request_info else None,
        "question_options": request_info.get("options") if request_info else None,
        "criteria": state.get("criteria"),
        "pending_slot": state.get("pending_slot"),
        "show_items_count": row["summary"].get("show_items_count"),
    }


def normalize(value):
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def core_observable(row: dict) -> dict:
    value = observable(row)
    value.pop("question_options", None)
    return normalize(value)


def latency_summary(rows: list[dict]) -> dict:
    wall = [float(row["elapsed_ms"]) for row in rows]
    pre_search = [
        float(row["summary"].get("stage_latency_ms", {}).get("pre_search_validator", 0.0))
        for row in rows
    ]
    return {
        "total_wall_ms": round(sum(wall), 2),
        "avg_wall_ms": round(statistics.mean(wall), 2),
        "p50_wall_ms": percentile(wall, 0.50),
        "p95_wall_ms": percentile(wall, 0.95),
        "max_wall_ms": round(max(wall), 2),
        "avg_pre_search_ms": round(statistics.mean(pre_search), 2),
    }


baseline = json.loads(Path(".tmp/deterministic_ask_baseline_50.json").read_text(encoding="utf-8"))
enabled = json.loads(Path(".tmp/deterministic_ask_enabled_50.json").read_text(encoding="utf-8"))
baseline_by_id = {row["case_id"]: row for row in baseline}
enabled_by_id = {row["case_id"]: row for row in enabled}

changed_to_ask = []
observable_differences = []
core_differences = []
option_changes = []
reply_text_differences = []
for case_id in baseline_by_id:
    before = baseline_by_id[case_id]
    after = enabled_by_id[case_id]
    before_path = before["summary"].get("pre_search_path")
    after_path = after["summary"].get("pre_search_path")
    if before_path == "llm" and after_path == "deterministic_ask":
        changed_to_ask.append(
            {
                "case_id": case_id,
                "message": before["request"]["message"]["text"],
                "before_ms": before["elapsed_ms"],
                "after_ms": after["elapsed_ms"],
                "saved_ms": round(float(before["elapsed_ms"]) - float(after["elapsed_ms"]), 2),
                "reduction_pct": round(
                    (1 - float(after["elapsed_ms"]) / float(before["elapsed_ms"])) * 100,
                    2,
                ),
                "question_key": observable(after)["question_key"],
            }
        )
    before_observable = observable(before)
    after_observable = observable(after)
    if before_observable != after_observable:
        observable_differences.append(
            {
                "case_id": case_id,
                "message": before["request"]["message"]["text"],
                "before": before_observable,
                "after": after_observable,
            }
        )
    if core_observable(before) != core_observable(after):
        core_differences.append(case_id)
    if before_observable["question_options"] != after_observable["question_options"]:
        option_changes.append(
            {
                "case_id": case_id,
                "before": before_observable["question_options"],
                "after": after_observable["question_options"],
            }
        )
    if before["summary"].get("reply_text") != after["summary"].get("reply_text"):
        reply_text_differences.append(case_id)

baseline_latency = latency_summary(baseline)
enabled_latency = latency_summary(enabled)
changed_before = [baseline_by_id[row["case_id"]] for row in changed_to_ask]
changed_after = [enabled_by_id[row["case_id"]] for row in changed_to_ask]

result = {
    "cases_total": len(baseline),
    "baseline_paths": dict(Counter(row["summary"].get("pre_search_path") for row in baseline)),
    "enabled_paths": dict(Counter(row["summary"].get("pre_search_path") for row in enabled)),
    "baseline_latency": baseline_latency,
    "enabled_latency": enabled_latency,
    "overall_saved_ms": round(baseline_latency["total_wall_ms"] - enabled_latency["total_wall_ms"], 2),
    "overall_reduction_pct": round(
        (1 - enabled_latency["total_wall_ms"] / baseline_latency["total_wall_ms"]) * 100,
        2,
    ),
    "changed_to_deterministic_ask_count": len(changed_to_ask),
    "changed_cases_baseline_latency": latency_summary(changed_before),
    "changed_cases_enabled_latency": latency_summary(changed_after),
    "observable_differences_count": len(observable_differences),
    "core_differences_count": len(core_differences),
    "core_difference_case_ids": core_differences,
    "option_changes_count": len(option_changes),
    "option_changes": option_changes,
    "reply_text_differences_count": len(reply_text_differences),
    "reply_text_difference_case_ids": reply_text_differences,
    "changed_to_deterministic_ask": changed_to_ask,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
