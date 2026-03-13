from datetime import datetime, timezone
from pathlib import Path


def generate_target_model_name(*, prefix: str, now: datetime | None = None) -> str:
    reference = now or datetime.now(timezone.utc)
    return f"{prefix}-{reference.strftime('%Y%m%d%H%M%S')}"


def benchmark_sort_key(result: dict[str, float | int | str]) -> tuple[float, float, float, float, float, float, float]:
    return (
        float(result.get("case_pass_pct", 0.0)),
        float(result.get("decision_accuracy_pct", 0.0)),
        float(result.get("criteria_accuracy_pct", 0.0)),
        float(result.get("missing_fields_accuracy_pct", 0.0)),
        float(result.get("next_question_key_accuracy_pct", 0.0)),
        -float(result.get("latency_p50_ms", 0.0)),
        -float(result.get("latency_avg_ms", 0.0)),
    )


def candidate_is_better(*, baseline: dict[str, float | int | str], candidate: dict[str, float | int | str]) -> bool:
    return benchmark_sort_key(candidate) > benchmark_sort_key(baseline)


def update_env_llm_model(*, env_path: Path, new_model_name: str) -> None:
    content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = content.splitlines()
    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith("LLM_MODEL="):
            new_lines.append(f"LLM_MODEL={new_model_name}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"LLM_MODEL={new_model_name}")
    env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
