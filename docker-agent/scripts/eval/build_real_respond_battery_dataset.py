"""Build the curated, versioned real-response battery and its review checklist."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATASET_PATH = Path("docs/assets/datasets/battery_structural_respond_v2.json")
REVIEW_PATH = Path("docs/assets/datasets/real_respond_battery_human_validation.md")


def turn(turn_id: str, message: str, expect: dict[str, Any] | None = None,
         schema_version: str = "1.0") -> dict[str, Any]:
    return {"id": turn_id, "message": message, "schema_version": schema_version,
            "expect": expect or {"status": 200}}


def scenario(scenario_id: str, category: str, tier: str, turns: list[dict[str, Any]],
             *, legacy: list[str] | None = None, review_reason: str | None = None,
             validation_question: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"id": scenario_id, "category": category, "tier": tier,
                           "turns": turns}
    if legacy:
        row["legacy_case_ids"] = legacy
    if review_reason:
        row.update({"review_required": True, "review_reason": review_reason,
                    "validation_question": validation_question})
    return row


def legacy_scenarios() -> list[dict[str, Any]]:
    base = [
        ("complete", "radiador gol 2010 1.0"),
        ("complete", "radiador ecosport 2008 1.6"),
        ("typo_complete", "rdiador ecosport 2008 1.6"),
        ("complete_alias", "radiador motor gol 2010 1.0"),
        ("complete", "coxim amortecedor ecosport 2008 1.6"),
        ("typo_complete", "coxin amortecedor ecosport 2008 1.6"),
        ("complete_alias", "coxim amort ecosport 2008 1.6"),
        ("complete_alias", "coxins amortecedor ecosport 2008 1.6"),
        ("complete", "pastilha de freio gol 2010 1.0"),
        ("typo_complete", "pstilhas de freio gol 2010 1.0"),
        ("complete_alias", "pastilhas freio gol 2010 1.0"),
        ("complete_alias", "pastilha gol 2010 1.0"),
        ("complete", "disco de freio gol 2010 dianteiro"),
        ("complete_alias", "radiadores motor ecosport 2008 1.6"),
        ("complete_alias", "radiadores arrefecimento gol 2010 1.0"),
        ("partial", "radiador gol 2010"),
        ("partial", "radiador ecosport 2008"),
        ("partial", "coxim amortecedor ecosport 2008"),
        ("partial", "pastilha de freio gol 2010"),
        ("partial", "filtro de oleo gol 2010"),
        ("partial", "bandeja ecosport 2008"),
        ("partial", "filtro de combustivel gol 2010"),
        ("partial", "filtro ar motor gol 2010"),
        ("partial", "disco de freio gol 2010"),
        ("partial", "farol gol 2010"),
        ("partial", "radiador focus 2010"),
        ("partial", "coxim amortecedor ecosport 2008"),
        ("partial", "pastilha de freio ecosport 2008"),
        ("partial_generic", "quero uma peca"),
        ("partial_generic", "preciso de ajuda com uma peca do gol"),
    ]
    followups = {
        16: "1.0", 17: "1.6", 18: "1.6", 19: "1.0", 20: "dianteiro",
        21: "dianteiro", 22: "esquerdo", 23: "dianteiro", 24: "dianteiro",
        25: "esquerdo", 26: "1.6", 27: "zetec rocam", 28: "1.6",
        29: "radiador gol 2010", 30: "pastilha de freio 2010 1.0",
    }
    strong: dict[int, dict[str, Any]] = {
        1: {"status": 200, "pre_search_path": "deterministic_bypass", "used_tools_contains": ["search_parts"]},
        9: {"status": 200, "question_key": "position", "pre_search_path": "deterministic_ask", "part_code": None},
        16: {"status": 200, "question_key": "engine", "pre_search_path": "deterministic_ask"},
        20: {"status": 200, "used_tools_contains": ["search_parts"], "used_tools_excludes": ["pre_search_deterministic_ask"]},
        21: {"status": 200, "question_key": "side", "pre_search_path": "deterministic_ask"},
        22: {"status": 200, "question_key_excludes": ["side"]},
        23: {"status": 200, "question_key_excludes": ["axle"]},
        29: {"status": 200, "question_key": "part_query", "pre_search_path": "deterministic_ask"},
    }
    smoke = {1, 9, 16, 20, 21, 22, 23, 29}
    rows: list[dict[str, Any]] = []
    for index, (category, message) in enumerate(base, 1):
        turns = [turn(f"legacy_{index:03d}_t1", message, strong.get(index))]
        legacy = [f"case_{index:03d}"]
        if index in followups:
            followup_id = index + 15
            turns.append(turn(f"legacy_{index:03d}_t2", followups[index]))
            legacy.append(f"case_{followup_id:03d}")
        rows.append(scenario(f"legacy_{index:03d}", category, "smoke" if index in smoke else "regression", turns, legacy=legacy))
    extras = [
        (46, "validation_error", "   ", "1.0", 400),
        (47, "validation_error", "Oi", "2.0", 400),
        (48, "typo_partial", "rdiador gol 2010", "1.0", 200),
        (49, "typo_partial", "pstilhas gol 2010", "1.0", 200),
        (50, "typo_complete", "bndejas ecosport 2008 eixo dianteiro", "1.0", 200),
    ]
    for index, category, message, version, status in extras:
        expect: dict[str, Any] = {"status": status}
        if index == 48:
            expect.update({"question_key": "engine", "part_code": None})
        if index == 49:
            expect.update({"question_key": "position", "part_code": None})
        if index == 50:
            expect.update({"question_key": "side", "part_code": None})
        rows.append(scenario(f"legacy_{index:03d}", category,
                             "smoke" if index in {46, 47, 50} else "regression",
                             [turn(f"legacy_{index:03d}_t1", message, expect, version)],
                             legacy=[f"case_{index:03d}"]))
    return rows


def deterministic_ask_scenarios() -> list[dict[str, Any]]:
    specs = [
        ("engine", "radiador {vehicle}", "radiador"),
        ("engine", "preciso de radiador para {vehicle}", "radiador"),
        ("engine", "coxim amortecedor {vehicle}", "coxim amortecedor"),
        ("position", "pastilha de freio {vehicle}", "pastilhas de freio"),
        ("engine", "disco de freio {vehicle} dianteiro", "discos de freio"),
        ("side", "bandeja {vehicle}", "bandejas"),
    ]
    vehicles = ["gol 2010", "ecosport 2008", "focus 2010", "gol ano 2010", "ford ecosport 2008"]
    rows: list[dict[str, Any]] = []
    index = 0
    for key, template, part_query in specs:
        for vehicle in vehicles:
            index += 1
            rows.append(scenario(
                f"ask_{index:03d}", "deterministic_ask", "smoke" if index <= 5 else "regression",
                [turn(f"ask_{index:03d}_t1", template.format(vehicle=vehicle), {
                    "status": 200, "action_type": "request_info", "question_key": key,
                    "pending_slot": key, "pre_search_path": "deterministic_ask",
                    "used_tools_contains": ["pre_search_deterministic_ask"],
                    "used_tools_excludes": ["search_parts"], "part_code": None,
                    "criteria_contains": {"part_query": part_query},
                })],
            ))
    return rows


def complete_search_scenarios() -> list[dict[str, Any]]:
    messages = [
        "radiador gol 2010 1.0", "radiador gol 2010 1.6", "radiador ecosport 2008 1.6",
        "rdiador ecosport 2008 1.6", "radiador focus 2010 1.6",
        "coxim amortecedor ecosport 2008 1.6", "coxin amortecedor ecosport 2008 1.6",
        "coxim amort ecosport 2008 zetec rocam dianteiro", "coxins amortecedor gol 2010 1.0",
        "coxim do amortecedor focus 2010 1.6",
        "pastilha de freio gol 2010 1.0 dianteira", "pastilhas freio gol 2010 1.0 traseira",
        "pstilhas ecosport 2008 1.6 dianteira", "pastilha focus 2010 1.6 dianteira",
        "pastilha de freio ecosport 2008 1.6 traseira",
        "disco de freio gol 2010 1.0 dianteiro", "discos freio gol 2010 1.6 traseiro",
        "disco de freio ecosport 2008 1.6 dianteiro", "disco focus 2010 1.6 dianteiro",
        "discos de freio ecosport 2008 1.6 traseiro",
        "bandeja ecosport 2008 esquerda", "bandeja ecosport 2008 direita",
        "bndejas ecosport 2008 lado esquerdo", "bandeja gol 2010 lado direito",
        "bandeja focus 2010 esquerda",
        "filtro de oleo gol 2010", "filtro oleo ecosport 2008", "filtro ar motor gol 2010",
        "filtro de combustivel gol 2010", "filtro de ar do motor ecosport 2008",
    ]
    rows: list[dict[str, Any]] = []
    for index, message in enumerate(messages, 1):
        rows.append(scenario(
            f"search_{index:03d}", "complete_search", "smoke" if index <= 5 else "regression",
            [turn(f"search_{index:03d}_t1", message, {
                "status": 200, "pre_search_path": "deterministic_bypass",
                "used_tools_contains": ["search_parts"], "part_code": None,
                "handoff_required": False,
            })],
            review_reason="O ERP pode mudar candidatos, discriminador e ordenacao." if index in {1, 3, 6, 11, 16, 21, 26} else None,
            validation_question="A familia entendida, os filtros e o primeiro discriminador fazem sentido comercialmente?" if index in {1, 3, 6, 11, 16, 21, 26} else None,
        ))
    return rows


def provenance_scenarios() -> list[dict[str, Any]]:
    invented = [
        "pastilha de freio 2010 1.0", "pastilha para gol 2010 1.0", "freio gol 2010",
        "radiador gol 2010", "bandeja ecosport 2008", "disco de freio focus 2010",
        "filtro gol 2010", "coxim ecosport 2008", "farol gol 2010", "peca gol 2010",
    ]
    literal = ["codigo AB-1234", "procure AB-5678", "peca XP-9012", "item RAD-4321", "codigo BDJ-9876"]
    rows: list[dict[str, Any]] = []
    for index, message in enumerate(invented, 1):
        rows.append(scenario(f"provenance_{index:03d}", "part_code_provenance",
                             "smoke" if index <= 3 else "regression",
                             [turn(f"provenance_{index:03d}_t1", message,
                                   {"status": 200, "part_code": None,
                                    "reply_excludes": ["FREIO-2010", "GOL-2010"]})]))
    for offset, message in enumerate(literal, len(invented) + 1):
        code = message.split()[-1]
        rows.append(scenario(f"provenance_{offset:03d}", "literal_part_code", "regression",
                             [turn(f"provenance_{offset:03d}_t1", message,
                                   {"status": 200, "part_code": code,
                                    "used_tools_contains": ["search_parts"]})]))
    return rows


def disambiguation_scenarios() -> list[dict[str, Any]]:
    starts = [
        "radiador gol 2010 1.0", "radiador ecosport 2008 1.6", "coxim amortecedor ecosport 2008 1.6",
        "bandeja ecosport 2008 esquerda", "radiador focus 2010 1.6",
        "radiador gol 2010 1.6", "coxim amortecedor gol 2010 1.0",
        "bandeja ecosport 2008 direita", "radiador ecosport 2008 1.6 zetec rocam",
        "radiador motor gol 2010 1.0",
    ]
    endings = ["1", "nenhuma dessas", "quero falar com um vendedor", "2", "talvez",
               "1", "nenhuma dessas", "2", "a primeira", "nao sei"]
    rows: list[dict[str, Any]] = []
    for index, (start, ending) in enumerate(zip(starts, endings), 1):
        turns = [turn(f"disambiguation_{index:03d}_t1", start, {
            "status": 200, "action_type_one_of": ["request_info", "show_items"],
            "used_tools_contains": ["search_parts"], "handoff_required": False,
        })]
        if ending == "quero falar com um vendedor":
            follow_expect = {"status": 200, "handoff_required": True}
        elif ending == "nenhuma dessas":
            follow_expect = {"status": 200, "pending_slot": "no_match_retry", "handoff_required": False}
        else:
            follow_expect = {"status": 200, "pre_search_path_one_of": ["result_disambiguation", "llm", "deterministic_bypass"]}
        turns.append(turn(f"disambiguation_{index:03d}_t2", ending, follow_expect))
        if index in {5, 10}:
            turns.extend([turn(f"disambiguation_{index:03d}_t3", "aquela"),
                          turn(f"disambiguation_{index:03d}_t4", "indefinido", {"status": 200})])
        rows.append(scenario(
            f"disambiguation_{index:03d}", "result_disambiguation", "regression",
            turns, review_reason="A selecao depende dos atributos e candidatos atuais do ERP.",
            validation_question="As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?",
        ))
    rows.append(scenario(
        "disambiguation_correction_001",
        "result_disambiguation_correction",
        "regression",
        [
            turn("disambiguation_correction_001_t1", "radiador Gol 2010 1.0", {
                "status": 200,
                "used_tools_contains": ["search_parts"],
            }),
            turn("disambiguation_correction_001_t2", "corrigindo, o carro e um Corsa 2011 1.4", {
                "status": 200,
                "criteria_contains": {
                    "part_query": "radiador",
                    "vehicle_model": "Corsa",
                    "vehicle_year": 2011,
                    "engine": "1.4",
                },
                "used_tools_contains": ["search_parts"],
                "used_tools_excludes": ["result_disambiguation"],
            }),
        ],
        review_reason="A correcao precisa descartar os candidatos da aplicacao anterior antes de pesquisar de novo.",
        validation_question="A segunda busca usa somente Corsa 2011 1.4 e nao permite selecionar um candidato do Gol?",
    ))
    return rows


def policy_scenarios() -> list[dict[str, Any]]:
    messages = [
        "meu carro esta esquentando, o que pode ser?", "tem aquilo que segura o carro?",
        "a peca faz barulho quando viro", "quero falar com um vendedor",
        "preciso de uma peca mas nao sei o nome", "voces vendem pneu?",
        "quero trocar o oleo inteiro", "o carro nao liga",
        "tem uma coisa perto do motor vazando", "agora quero uma bateria para o carro",
    ]
    rows: list[dict[str, Any]] = []
    for index, message in enumerate(messages, 1):
        rows.append(scenario(
            f"policy_{index:03d}", "semantic_or_policy", "extended",
            [turn(f"policy_{index:03d}_t1", message, {"status": 200})],
            review_reason="Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.",
            validation_question="A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?",
        ))
    return rows


def safety_resolution_scenarios() -> list[dict[str, Any]]:
    """Regression cases that must be resolved before any catalog search."""
    specs = [
        (
            "safety_001",
            "pastilha traseira do Gol 2010, nao dianteira",
            {
                "status": 200,
                "pre_search_path": "deterministic_bypass",
                "criteria_contains": {"part_query": "pastilhas de freio", "position": "rear"},
                "used_tools_contains": ["search_parts"],
            },
        ),
        (
            "safety_002",
            "nao quero radiador, quero filtro de oleo Gol 2010 1.0",
            {
                "status": 200,
                "pre_search_path": "deterministic_bypass",
                "criteria_contains": {"part_query": "filtro de oleo", "engine": "1.0"},
                "used_tools_contains": ["search_parts"],
            },
        ),
        (
            "safety_003",
            "nao quero radiador",
            {
                "status": 200,
                "pre_search_path": "deterministic_ask",
                "question_key": "intent_resolution",
                "used_tools_excludes": ["search_parts"],
            },
        ),
        (
            "safety_004",
            "pastilha Honda Gol 2010 traseira",
            {
                "status": 200,
                "pre_search_path": "deterministic_ask",
                "question_key": "vehicle_identity",
                "used_tools_excludes": ["search_parts"],
            },
        ),
    ]
    return [
        scenario(scenario_id, "safety_resolution", "regression", [turn(f"{scenario_id}_t1", message, expect)])
        for scenario_id, message, expect in specs
    ]


def multi_item_vehicle_context_scenarios() -> list[dict[str, Any]]:
    specs = [
        (
            "multi_vehicle_001",
            "radiador Gol 2010 1.0 e radiador Corsa 2011 1.4",
            [
                {"part_query": "radiador", "vehicle_model": "Gol", "vehicle_year": 2010, "engine": "1.0"},
                {"part_query": "radiador", "vehicle_model": "Corsa", "vehicle_year": 2011, "engine": "1.4"},
            ],
        ),
        (
            "multi_vehicle_002",
            "radiador Gol 2010 1.0 e pastilha de freio traseira",
            [
                {"part_query": "radiador", "vehicle_model": "Gol", "vehicle_year": 2010, "engine": "1.0"},
                {"part_query": "pastilhas de freio", "position": "rear", "vehicle_model": None, "vehicle_year": None, "engine": None},
            ],
        ),
        (
            "multi_vehicle_003",
            "radiador e pastilha de freio traseira para Gol 2010 1.0",
            [
                {"part_query": "radiador", "vehicle_model": "Gol", "vehicle_year": 2010, "engine": "1.0"},
                {"part_query": "pastilhas de freio", "position": "rear", "vehicle_model": "Gol", "vehicle_year": 2010, "engine": "1.0"},
            ],
        ),
    ]
    return [
        scenario(
            scenario_id,
            "multi_item_vehicle_context",
            "regression",
            [turn(f"{scenario_id}_t1", message, {
                "status": 200,
                "items_contains": expected_items,
                "used_tools_contains": ["search_parts"],
            })],
        )
        for scenario_id, message, expected_items in specs
    ]


def multi_item_gate_scenarios() -> list[dict[str, Any]]:
    return [
        scenario(
            "multi_gate_001",
            "multi_item_gate",
            "regression",
            [turn(
                "multi_gate_001_t1",
                "radiador Gol 2010 1.0 e bandeja Corsa 2011",
                {
                    "status": 200,
                    "items_contains": [
                        {"part_query": "radiador", "vehicle_model": "Gol", "vehicle_year": 2010, "engine": "1.0"},
                        {"part_query": "bandejas", "vehicle_model": "Corsa", "vehicle_year": 2011, "engine": None},
                    ],
                    "item_results_contains": [
                        {"item": {"part_query": "radiador", "vehicle_model": "Gol", "engine": "1.0"}},
                        {"status": "incomplete", "item": {"part_query": "bandejas", "vehicle_model": "Corsa", "engine": None}},
                    ],
                    "used_tools_contains": ["search_parts"],
                },
            )],
        )
    ]


def multi_item_follow_up_scenarios() -> list[dict[str, Any]]:
    return [
        scenario(
            "multi_follow_up_001",
            "multi_item_follow_up",
            "regression",
            [
                turn(
                    "multi_follow_up_001_t1",
                    "radiador Gol 2010 1.0 e bandeja Corsa 2011",
                    {
                        "status": 200,
                        "pending_slot": "side",
                        "active_item_index": 1,
                        "item_results_contains": [
                            {"item": {"part_query": "radiador", "vehicle_model": "Gol", "engine": "1.0"}},
                            {"status": "incomplete", "item": {"part_query": "bandejas", "vehicle_model": "Corsa"}},
                        ],
                    },
                ),
                turn(
                    "multi_follow_up_001_t2",
                    "esquerda",
                    {
                        "status": 200,
                        "pending_slot": None,
                        "active_item_index": None,
                        "items_contains": [
                            {"part_query": "radiador", "vehicle_model": "Gol", "engine": "1.0"},
                            {"part_query": "bandejas", "vehicle_model": "Corsa", "side": "left"},
                        ],
                        "item_results_contains": [
                            {"item": {"part_query": "radiador", "vehicle_model": "Gol", "engine": "1.0"}},
                            {"item": {"part_query": "bandejas", "vehicle_model": "Corsa", "side": "left"}},
                        ],
                        "used_tools_count": {"search_parts": 1},
                    },
                ),
            ],
        )
    ]


def validation_scenarios() -> list[dict[str, Any]]:
    specs = [("", "1.0"), (" ", "1.0"), ("\t", "1.0"), ("Oi", "0.9"), ("radiador", "99.0")]
    return [scenario(f"invalid_{index:03d}", "contract_validation", "regression",
                     [turn(f"invalid_{index:03d}_t1", message, {"status": 400}, version)])
            for index, (message, version) in enumerate(specs, 1)]


def build_document() -> dict[str, Any]:
    scenarios = (legacy_scenarios() + deterministic_ask_scenarios() +
                 complete_search_scenarios() + provenance_scenarios() +
                 disambiguation_scenarios() + policy_scenarios() +
                 safety_resolution_scenarios() + multi_item_vehicle_context_scenarios() +
                 multi_item_gate_scenarios() +
                 multi_item_follow_up_scenarios() +
                 validation_scenarios())
    return {
        "schema_version": "2.0", "name": "real_respond_battery_v2",
        "description": "Bateria multi-turno estrutural para docker-agent e docker-comm.",
        "curation_status": "structural assertions approved; flagged commercial cases require human review",
        "tier_semantics": {
            "smoke": "fluxos criticos e deterministas para cada alteracao",
            "regression": "smoke mais cobertura estrutural ampla",
            "extended": "regression mais linguagem incerta e politica dependente da LLM",
        },
        "scenarios": scenarios,
    }


def render_review(document: dict[str, Any]) -> str:
    rows = [item for item in document["scenarios"] if item.get("review_required")]
    lines = ["# Lista de validacao humana da bateria real", "",
             "Estes cenarios ja possuem validacoes automatizadas estruturais. A revisao abaixo serve para promover expectativas comerciais; ela nao deve ser preenchida pelo modelo.", "",
             "Marque cada item depois de testar no Streamlit e registre a resposta esperada quando houver produto, discriminador ou handoff especifico.", ""]
    for item in rows:
        messages = " → ".join(f'`{turn_row["message"]}`' for turn_row in item["turns"])
        lines.extend([
            f"- [ ] **{item['id']} — {item['category']}**",
            f"  - conversa: {messages}",
            f"  - por que revisar: {item['review_reason']}",
            f"  - validar: {item['validation_question']}",
            "  - resultado esperado aprovado: _preencher_",
            "",
        ])
    return "\n".join(lines)


def main() -> None:
    document = build_document()
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATASET_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REVIEW_PATH.write_text(render_review(document), encoding="utf-8")
    print(json.dumps({
        "dataset": DATASET_PATH.as_posix(), "review": REVIEW_PATH.as_posix(),
        "scenarios": len(document["scenarios"]),
        "turns": sum(len(item["turns"]) for item in document["scenarios"]),
        "human_review": sum(bool(item.get("review_required")) for item in document["scenarios"]),
    }))


if __name__ == "__main__":
    main()
