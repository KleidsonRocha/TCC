import json
from pathlib import Path
from typing import Any

from app.config import Settings
from app.infra.logger import configure_logging, get_logger
from app.infra.pre_search_validator_llm import LLMPreSearchValidator


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_validator(settings: Settings):
    logger = get_logger("pre-search-eval")
    return LLMPreSearchValidator(settings=settings, logger=logger)


def _as_context(raw_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"role": str(item.get("role", "user")), "text": str(item.get("text", ""))} for item in raw_context]


def _slot_match(predicted: Any, expected: Any) -> bool:
    if isinstance(predicted, str) and isinstance(expected, str):
        return predicted.strip().lower() == expected.strip().lower()
    return predicted == expected


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    validator = _pick_validator(settings)
    dataset_path = Path("docs/pre_search_eval_dataset_mvp.json")
    rows = _load_dataset(dataset_path)

    decision_ok = 0
    next_question_ok = 0
    next_question_total = 0
    slot_total = 0
    slot_ok = 0
    slots = ("part_query", "vehicle_brand", "vehicle_model", "vehicle_year", "engine", "side")

    for row in rows:
        message = str(row.get("message.text", ""))
        context = _as_context(row.get("context.last_messages", []))
        expected = row.get("expected", {})
        result = validator.validate(message_text=message, last_messages=context)

        if result.decision == expected.get("decision"):
            decision_ok += 1

        expected_q = expected.get("next_question")
        if expected_q:
            next_question_total += 1
            predicted_key = result.next_question.key if result.next_question else None
            if predicted_key == expected_q.get("key"):
                next_question_ok += 1

        expected_criteria = expected.get("criteria", {})
        for slot in slots:
            if slot not in expected_criteria:
                continue
            slot_total += 1
            predicted_value = getattr(result.criteria, slot, None)
            expected_value = expected_criteria.get(slot)
            if _slot_match(predicted_value, expected_value):
                slot_ok += 1

    total = max(len(rows), 1)
    decision_accuracy = (decision_ok / total) * 100
    slot_accuracy = (slot_ok / max(slot_total, 1)) * 100
    next_question_utility = (next_question_ok / max(next_question_total, 1)) * 100

    print(json.dumps(
        {
            "dataset_size": len(rows),
            "decision_accuracy_pct": round(decision_accuracy, 2),
            "slot_extraction_accuracy_pct": round(slot_accuracy, 2),
            "next_question_utility_pct": round(next_question_utility, 2),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
