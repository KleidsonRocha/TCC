import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


API_URL = "http://localhost:8001/respond"
OUTPUT_JSON = Path("docs/assets/reports/real_respond_battery_2026-03-25.json")
OUTPUT_MD = Path("docs/assets/reports/real_respond_battery_2026-03-25.md")
TRACE_PREFIX = "real-battery-20260325"


@dataclass(frozen=True)
class Case:
    case_id: str
    category: str
    conversation_id: str
    message_text: str
    schema_version: str = "1.0"
    parent_case_id: str | None = None


CASES: list[Case] = [
    Case("case_001", "complete", "conv-radiador-gol-direct-001", "radiador gol 2010 1.0"),
    Case("case_002", "complete", "conv-radiador-ecosport-direct-001", "radiador ecosport 2008 1.6"),
    Case("case_003", "typo_complete", "conv-radiador-ecosport-typo-001", "rdiador ecosport 2008 1.6"),
    Case("case_004", "complete_alias", "conv-radiador-gol-alias-001", "radiador motor gol 2010 1.0"),
    Case("case_005", "complete", "conv-coxim-ecosport-direct-001", "coxim amortecedor ecosport 2008 1.6"),
    Case("case_006", "typo_complete", "conv-coxim-ecosport-typo-001", "coxin amortecedor ecosport 2008 1.6"),
    Case("case_007", "complete_alias", "conv-coxim-ecosport-alias-001", "coxim amort ecosport 2008 1.6"),
    Case("case_008", "complete_alias", "conv-coxim-ecosport-plural-001", "coxins amortecedor ecosport 2008 1.6"),
    Case("case_009", "complete", "conv-pastilha-gol-direct-001", "pastilha de freio gol 2010 1.0"),
    Case("case_010", "typo_complete", "conv-pastilha-gol-typo-001", "pstilhas de freio gol 2010 1.0"),
    Case("case_011", "complete_alias", "conv-pastilha-gol-alias-001", "pastilhas freio gol 2010 1.0"),
    Case("case_012", "complete_alias", "conv-pastilha-gol-short-001", "pastilha gol 2010 1.0"),
    Case("case_013", "complete", "conv-disco-gol-direct-001", "disco de freio gol 2010 dianteiro"),
    Case("case_014", "complete_alias", "conv-radiador-ecosport-plural-001", "radiadores motor ecosport 2008 1.6"),
    Case("case_015", "complete_alias", "conv-radiador-gol-plural-001", "radiadores arrefecimento gol 2010 1.0"),
    Case("case_016", "partial", "conv-radiador-gol-follow-001", "radiador gol 2010"),
    Case("case_017", "partial", "conv-radiador-ecosport-follow-001", "radiador ecosport 2008"),
    Case("case_018", "partial", "conv-coxim-ecosport-follow-num-001", "coxim amortecedor ecosport 2008"),
    Case("case_019", "partial", "conv-pastilha-gol-follow-001", "pastilha de freio gol 2010"),
    Case("case_020", "partial", "conv-filtro-oleo-gol-follow-001", "filtro de oleo gol 2010"),
    Case("case_021", "partial", "conv-bandeja-ecosport-follow-001", "bandeja ecosport 2008"),
    Case("case_022", "partial", "conv-filtro-comb-gol-follow-001", "filtro de combustivel gol 2010"),
    Case("case_023", "partial", "conv-filtro-ar-gol-follow-001", "filtro ar motor gol 2010"),
    Case("case_024", "partial", "conv-disco-gol-follow-001", "disco de freio gol 2010"),
    Case("case_025", "partial", "conv-farol-gol-follow-001", "farol gol 2010"),
    Case("case_026", "partial", "conv-radiador-focus-follow-001", "radiador focus 2010"),
    Case("case_027", "partial", "conv-coxim-ecosport-follow-text-001", "coxim amortecedor ecosport 2008"),
    Case("case_028", "partial", "conv-pastilha-ecosport-follow-001", "pastilha de freio ecosport 2008"),
    Case("case_029", "partial_generic", "conv-generic-part-follow-001", "quero uma peca"),
    Case("case_030", "partial_generic", "conv-generic-gol-follow-001", "preciso de ajuda com uma peca do gol"),
    Case("case_031", "follow_up", "conv-radiador-gol-follow-001", "1.0", parent_case_id="case_016"),
    Case("case_032", "follow_up", "conv-radiador-ecosport-follow-001", "1.6", parent_case_id="case_017"),
    Case("case_033", "follow_up", "conv-coxim-ecosport-follow-num-001", "1.6", parent_case_id="case_018"),
    Case("case_034", "follow_up", "conv-pastilha-gol-follow-001", "1.0", parent_case_id="case_019"),
    Case("case_035", "follow_up", "conv-filtro-oleo-gol-follow-001", "dianteiro", parent_case_id="case_020"),
    Case("case_036", "follow_up", "conv-bandeja-ecosport-follow-001", "dianteiro", parent_case_id="case_021"),
    Case("case_037", "follow_up", "conv-filtro-comb-gol-follow-001", "esquerdo", parent_case_id="case_022"),
    Case("case_038", "follow_up", "conv-filtro-ar-gol-follow-001", "dianteiro", parent_case_id="case_023"),
    Case("case_039", "follow_up", "conv-disco-gol-follow-001", "dianteiro", parent_case_id="case_024"),
    Case("case_040", "follow_up", "conv-farol-gol-follow-001", "esquerdo", parent_case_id="case_025"),
    Case("case_041", "follow_up", "conv-radiador-focus-follow-001", "1.6", parent_case_id="case_026"),
    Case("case_042", "follow_up_text_engine", "conv-coxim-ecosport-follow-text-001", "zetec rocam", parent_case_id="case_027"),
    Case("case_043", "follow_up", "conv-pastilha-ecosport-follow-001", "1.6", parent_case_id="case_028"),
    Case("case_044", "follow_up", "conv-generic-part-follow-001", "radiador gol 2010", parent_case_id="case_029"),
    Case("case_045", "follow_up", "conv-generic-gol-follow-001", "pastilha de freio 2010 1.0", parent_case_id="case_030"),
    Case("case_046", "validation_error", "conv-invalid-empty-001", "   "),
    Case("case_047", "validation_error", "conv-invalid-schema-001", "Oi", schema_version="2.0"),
    Case("case_048", "typo_partial", "conv-radiador-typo-partial-001", "rdiador gol 2010"),
    Case("case_049", "typo_partial", "conv-pastilha-typo-partial-001", "pstilhas gol 2010"),
    Case("case_050", "typo_complete", "conv-bandeja-typo-direct-001", "bndejas ecosport 2008 eixo dianteiro"),
]


def build_payload(case: Case, parent_result: dict[str, Any] | None) -> dict[str, Any]:
    last_messages: list[dict[str, str]] = []
    conversation_state: dict[str, Any] | None = None
    if parent_result:
        parent_request = parent_result["request"]
        parent_response = parent_result.get("response") or {}
        last_messages = [
            {
                "role": "user",
                "text": str(parent_request["message"]["text"]),
            },
            {
                "role": "assistant",
                "text": str(parent_response.get("reply", {}).get("text", "")),
            },
        ]
        conversation_state = parent_response.get("conversation_state")

    return {
        "schema_version": case.schema_version,
        "trace_id": f"{TRACE_PREFIX}-{case.case_id}",
        "conversation_id": case.conversation_id,
        "channel": {"name": "manual-real-battery"},
        "message": {"text": case.message_text},
        "context": {
            "last_messages": last_messages,
            "conversation_state": conversation_state,
        },
        "runtime": {"locale": "pt-BR", "timezone": "America/Sao_Paulo"},
        "business": {"branch_id": 1},
    }


def call_api(payload: dict[str, Any]) -> tuple[int, dict[str, Any], float]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started_at = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            status_code = int(response.status)
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status_code = int(exc.code)
        raw = exc.read().decode("utf-8")
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    return status_code, json.loads(raw), elapsed_ms


def summarize_case(case: Case, payload: dict[str, Any], status_code: int, body: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
    response_text = body.get("reply", {}).get("text") if isinstance(body, dict) else None
    actions = body.get("actions", []) if isinstance(body, dict) else []
    handoff = body.get("handoff", {}) if isinstance(body, dict) else {}
    tool_trace = body.get("tool_trace", {}) if isinstance(body, dict) else {}
    conversation_state = body.get("conversation_state") if isinstance(body, dict) else None
    show_items: list[dict[str, Any]] = []
    for action in actions:
        if action.get("type") == "show_items":
            show_items = list(action.get("items", []))
            break
    return {
        "case_id": case.case_id,
        "category": case.category,
        "parent_case_id": case.parent_case_id,
        "request": payload,
        "status_code": status_code,
        "elapsed_ms": elapsed_ms,
        "response": body,
        "summary": {
            "reply_text": response_text,
            "handoff_required": handoff.get("required"),
            "handoff_reason": handoff.get("reason"),
            "used_tools": tool_trace.get("used_tools", []),
            "latency_ms": tool_trace.get("latency_ms"),
            "stage_latency_ms": tool_trace.get("stage_latency_ms", {}),
            "pre_search_path": tool_trace.get("pre_search_path"),
            "actions_count": len(actions),
            "show_items_count": len(show_items),
            "top_items": show_items[:5],
            "conversation_state": conversation_state,
        },
    }


def category_stats(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for row in results:
        category = str(row["category"])
        bucket = stats.setdefault(
            category,
            {
                "cases": 0,
                "http_200": 0,
                "ask_like": 0,
                "show_items": 0,
                "handoff": 0,
                "errors": 0,
            },
        )
        bucket["cases"] += 1
        if int(row["status_code"]) == 200:
            bucket["http_200"] += 1
        else:
            bucket["errors"] += 1
        response = row.get("response") or {}
        actions = response.get("actions", []) if isinstance(response, dict) else []
        if any(action.get("type") == "request_info" for action in actions):
            bucket["ask_like"] += 1
        if any(action.get("type") == "show_items" for action in actions):
            bucket["show_items"] += 1
        handoff = response.get("handoff", {}) if isinstance(response, dict) else {}
        if handoff.get("required"):
            bucket["handoff"] += 1
    return stats


def render_md(results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Bateria Real De 50 Testes - 2026-03-25")
    lines.append("")
    lines.append("## Escopo")
    lines.append("")
    lines.append("Relatorio gerado por chamadas reais ao `POST /respond`, sem `StubPreSearchValidator`, `_FakeTools` ou `TestClient` sobrescrito.")
    lines.append("")
    lines.append(f"- total de testes executados: `{len(results)}`")
    lines.append(f"- endpoint: `{API_URL}`")
    lines.append(f"- trace prefix: `{TRACE_PREFIX}`")
    lines.append("")

    success = sum(1 for row in results if int(row["status_code"]) == 200)
    handoff = sum(1 for row in results if (row.get("response") or {}).get("handoff", {}).get("required"))
    show_items = sum(
        1
        for row in results
        if any(action.get("type") == "show_items" for action in (row.get("response") or {}).get("actions", []))
    )
    request_info = sum(
        1
        for row in results
        if any(action.get("type") == "request_info" for action in (row.get("response") or {}).get("actions", []))
    )
    errors = len(results) - success
    latencies = [float(row["elapsed_ms"]) for row in results]
    lines.append("## Resumo")
    lines.append("")
    lines.append(f"- respostas HTTP 200: `{success}`")
    lines.append(f"- respostas com `request_info`: `{request_info}`")
    lines.append(f"- respostas com `show_items`: `{show_items}`")
    lines.append(f"- respostas com `handoff.required=true`: `{handoff}`")
    lines.append(f"- erros HTTP: `{errors}`")
    lines.append(f"- latencia minima observada: `{min(latencies):.2f} ms`")
    lines.append(f"- latencia maxima observada: `{max(latencies):.2f} ms`")
    lines.append(f"- latencia media observada: `{(sum(latencies) / len(latencies)):.2f} ms`")
    lines.append("")

    lines.append("## Resumo Por Categoria")
    lines.append("")
    for category, stats in sorted(category_stats(results).items()):
        lines.append(
            f"- `{category}`: casos=`{stats['cases']}`, http_200=`{stats['http_200']}`, "
            f"request_info=`{stats['ask_like']}`, show_items=`{stats['show_items']}`, "
            f"handoff=`{stats['handoff']}`, erros=`{stats['errors']}`"
        )
    lines.append("")

    lines.append("## Casos")
    lines.append("")
    for row in results:
        response = row.get("response") or {}
        summary = row.get("summary") or {}
        reply_text = summary.get("reply_text")
        top_items = summary.get("top_items", [])
        lines.append(f"### {row['case_id']} - {row['category']}")
        lines.append("")
        lines.append(f"- `trace_id`: `{row['request']['trace_id']}`")
        lines.append(f"- `conversation_id`: `{row['request']['conversation_id']}`")
        if row.get("parent_case_id"):
            lines.append(f"- `parent_case_id`: `{row['parent_case_id']}`")
        lines.append(f"- pergunta: `{row['request']['message']['text']}`")
        lines.append(f"- status HTTP: `{row['status_code']}`")
        lines.append(f"- latencia total observada: `{row['elapsed_ms']} ms`")
        if int(row["status_code"]) != 200:
            lines.append(f"- erro: `{json.dumps(response, ensure_ascii=False)}`")
            lines.append("")
            continue
        lines.append(f"- resposta: `{reply_text}`")
        lines.append(f"- ferramentas usadas: `{summary.get('used_tools', [])}`")
        lines.append(f"- caminho de pre-busca: `{summary.get('pre_search_path')}`")
        lines.append(f"- latencia por etapa: `{summary.get('stage_latency_ms', {})}`")
        lines.append(f"- handoff: `{summary.get('handoff_required')}`")
        if summary.get("handoff_reason") is not None:
            lines.append(f"- handoff_reason: `{summary.get('handoff_reason')}`")
        lines.append(f"- actions: `{response.get('actions', [])}`")
        criteria = (summary.get("conversation_state") or {}).get("criteria") if isinstance(summary.get("conversation_state"), dict) else None
        if criteria:
            lines.append(f"- criteria em `conversation_state`: `{criteria}`")
        if top_items:
            lines.append("- top items:")
            for item in top_items:
                lines.append(
                    f"  - `{item.get('item_id')}` | `{item.get('title')}` | `score={item.get('score')}`"
                )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    results: list[dict[str, Any]] = []
    results_by_case_id: dict[str, dict[str, Any]] = {}

    for index, case in enumerate(CASES, start=1):
        parent_result = results_by_case_id.get(case.parent_case_id) if case.parent_case_id else None
        payload = build_payload(case, parent_result)
        status_code, body, elapsed_ms = call_api(payload)
        row = summarize_case(case, payload, status_code, body, elapsed_ms)
        results.append(row)
        results_by_case_id[case.case_id] = row
        print(
            json.dumps(
                {
                    "progress": f"{index}/{len(CASES)}",
                    "case_id": case.case_id,
                    "category": case.category,
                    "status_code": status_code,
                    "elapsed_ms": elapsed_ms,
                    "reply_text": row["summary"].get("reply_text"),
                    "handoff_required": row["summary"].get("handoff_required"),
                    "used_tools": row["summary"].get("used_tools"),
                    "pre_search_path": row["summary"].get("pre_search_path"),
                    "stage_latency_ms": row["summary"].get("stage_latency_ms"),
                    "show_items_count": row["summary"].get("show_items_count"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    OUTPUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(render_md(results), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_json": str(OUTPUT_JSON).replace("\\", "/"),
                "output_md": str(OUTPUT_MD).replace("\\", "/"),
                "cases_total": len(results),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
