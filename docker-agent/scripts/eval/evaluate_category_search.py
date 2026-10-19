"""Audit one conversation per category/subcategory against source ERP records.

Uses the real request use case in an isolated process, with no review writes.
Source checks are independent of the search SQL. Findings require human review;
one representative conversation does not measure recall over every ERP item.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import html
import json
import logging
from pathlib import Path
import re
import time
import uuid

import psycopg
from psycopg.rows import dict_row

from app.api.schemas.contract_v1 import AgentRequestV1
from app.config import Settings
from app.core.usecases.process_agent_request import ProcessAgentRequestUseCase
from app.infra.erp_search_tools_pg import resolve_search_tools
from app.infra.postgres_conninfo import build_catalog_conninfo, build_erp_conninfo
from app.infra.pre_search_catalog_pg import resolve_pre_search_catalog
from app.infra.pre_search_review_queue_pg import NoOpPreSearchReviewRecorder
from app.infra.pre_search_text import normalize_pre_search_text as norm
from app.infra.pre_search_validator_llm import LLMPreSearchValidator
from scripts.eval.run_real_respond_battery import normalize_response


def read_connection(conninfo):
    conn = psycopg.connect(conninfo, row_factory=dict_row, client_encoding="UTF8")
    conn.execute("SET TRANSACTION READ ONLY")
    conn.execute("SET LOCAL statement_timeout = '120s'")
    return conn


def reference_facts(item):
    if not item:
        return {}
    app = item.get("application") or {}
    title = norm((item.get("nm_item") or "") + " " + (item.get("candidate_title") or ""))
    facts = {}
    model = app.get("vehicle_model")
    if norm(model) not in {"", "todos", "universal", "-"}:
        facts["vehicle_model"] = model
        brand = app.get("vehicle_brand")
        if norm(brand) not in {"", "todos", "-"}:
            facts["vehicle_brand"] = brand
        start, end = app.get("year_start"), app.get("year_end")
        if start and start >= 1980 and (app.get("year_open_end") or end and end >= start):
            facts["vehicle_year"] = str(min(max(2010, start), end or max(2010, start)))
        for engine in app.get("engines") or []:
            match = re.search(r"\b([1-6]\.[0-9])\b", engine)
            if match:
                facts["engine"] = match[1]
                break
        if not facts.get("engine") and app.get("engines"):
            facts["engine"] = app["engines"][0]
        for variant in app.get("variants") or []:
            if norm(variant) not in {"", "todos", "-"}:
                facts["variant"] = variant
                break
    for key, patterns in {
        "side": [(r"\b(esquerd[oa]|esq|le)\b", "esquerdo"), (r"\b(direit[oa]|dir|ld)\b", "direito")],
        "position": [(r"\b(dianteir[oa]s?|diant)\b", "dianteiro"), (r"\b(traseir[oa]s?|tras)\b", "traseiro")],
        "axle": [(r"\beixo dianteir[oa]\b", "eixo dianteiro"), (r"\beixo traseir[oa]\b", "eixo traseiro")],
    }.items():
        for pattern, value in patterns:
            if re.search(pattern, title):
                facts[key] = value
                break
    viscosity = re.search(r"\b(\d{1,2})\s*w\s*-?\s*(\d{2})\b", title)
    if viscosity and norm(item.get("part_family")) == "lubrificantes":
        facts["variant"] = f"{viscosity[1]}W{viscosity[2]}"
    if "amortec" in title:
        facts["coxim_type"] = "amortecedor"
    elif "motor" in title or "cambio" in title:
        facts["coxim_type"] = "motor/cambio"
    return facts


def choose_reference(items, catalog):
    known = {norm(x) for x in catalog.model_aliases}
    def score(item):
        facts = reference_facts(item)
        family = norm(item.get("part_family"))
        required = {"variant"} if family == "lubrificantes" else {"vehicle_model", "vehicle_year"}
        for field in ("engine", "variant", "side", "position", "axle"):
            if family in getattr(catalog, "needs_" + field, set()):
                required.add(field)
        available = set(facts)
        if norm(facts.get("vehicle_model")) not in known:
            available.discard("vehicle_model")
        return (required <= available, len(required & available),
                norm(facts.get("vehicle_model")) in known, len(facts), -len(item.get("candidate_title") or ""))
    return max(items, key=score) if items else None


def reference_query(case, catalog):
    """Make a meaningful customer request, using no product code or future reply."""
    family = norm(case['family'])
    targets = defaultdict(set)
    for canonical, aliases in catalog.part_patterns:
        for alias in aliases:
            targets[alias].add(canonical)
    aliases = next((aliases for canonical, aliases in catalog.part_patterns if canonical == family), ())
    unambiguous = [a for a in aliases if targets[a] == {family}]
    label = family if family in unambiguous else min(unambiguous, key=lambda a: (len(a.split()), len(a)), default=family)
    reference = case.get('reference') or {}
    if family in catalog.generic_ambiguous_parts and reference:
        label = reference.get('candidate_title') or label
    facts = reference_facts(reference)
    if family == 'lubrificantes':
        # Exercise the general product-specification search, not a car filter.
        facts = {k: v for k, v in facts.items() if k == 'variant'}
    supplied = {}
    parts = [f"Preciso de {label}"]
    if facts.get('vehicle_model'):
        parts.append('para '+facts['vehicle_model'])
        supplied['vehicle_model'] = facts['vehicle_model']
    if facts.get('vehicle_year'):
        parts.append(facts['vehicle_year'])
        supplied['vehicle_year'] = facts['vehicle_year']
    if facts.get('engine'):
        parts.append('motor '+facts['engine'])
        supplied['engine'] = facts['engine']
    for field in ('side', 'position', 'axle'):
        if facts.get(field):
            parts.append(facts[field])
            supplied[field] = facts[field]
    if family == 'lubrificantes' and facts.get('variant'):
        parts.append(facts['variant'])
        supplied['variant'] = facts['variant']
    return ' '.join(parts), supplied


def prepare_cases(settings, catalog, sample_size, include_unmapped=False):
    with read_connection(build_catalog_conninfo(settings)) as conn:
        taxonomy = conn.execute("""SELECT g.source_group_code AS group_code, g.name AS group_name,
            t.source_subgroup_code AS subgroup_code, t.name AS family
            FROM pre_search_part_group g JOIN pre_search_part_type t ON t.part_group_id=g.id
            WHERE g.is_active AND t.is_active ORDER BY g.source_group_code,t.source_subgroup_code""").fetchall()
        groups = conn.execute("SELECT source_group_code AS group_code,name AS group_name FROM pre_search_part_group WHERE is_active ORDER BY source_group_code").fetchall()
    sources = [("erp_postgres", build_erp_conninfo(settings))] if settings.erp_db_enabled else []
    if settings.erp_fallback_db_enabled:
        sources.append(("local_fallback_postgres", build_catalog_conninfo(settings)))
    source = conninfo = None
    errors = []
    for name, info in sources:
        try:
            with read_connection(info) as conn:
                conn.execute("SELECT id_item FROM soccol.item_search_candidates LIMIT 1").fetchone()
            source, conninfo = name, info
            break
        except Exception as exc:
            errors.append({"source": name, "error_type": type(exc).__name__})
    if not conninfo:
        raise RuntimeError("Nenhuma fonte de busca acessivel para construir referencias")
    print(json.dumps({"phase": "source_sampling", "source": source}, ensure_ascii=False), flush=True)
    known_models = list(catalog.model_aliases)
    with read_connection(conninfo) as conn:
        inventory = conn.execute("SELECT cd_grupo,cd_subgrupo,min(part_family) AS family,count(*) AS count FROM soccol.item_search_candidates GROUP BY cd_grupo,cd_subgrupo").fetchall()
        samples = conn.execute("""WITH ranked AS (
            SELECT c.*,row_number() OVER(PARTITION BY cd_grupo,cd_subgrupo ORDER BY
                (lower(part_family)='lubrificantes' AND concat_ws(' ',nm_item,candidate_title) ~* '\\m[0-9]{1,2}\\s*w\\s*-?\\s*[0-9]{2}\\M') DESC,
                (candidate_title ~* '\\m(gol|corsa|palio|onix|ecosport|fiesta|uno)\\M') DESC,id_item) AS rn
            FROM soccol.item_search_candidates c
        ) SELECT c.*,to_jsonb(a) AS application FROM ranked c
        LEFT JOIN LATERAL (SELECT * FROM soccol.item_search_applications a WHERE a.id_item=c.id_item
            ORDER BY (a.vehicle_model=ANY(%s)) DESC NULLS LAST,
                (a.year_start BETWEEN 1980 AND 2026) DESC NULLS LAST,
                cardinality(a.engines) DESC NULLS LAST,a.application_id LIMIT 1) a ON TRUE
        WHERE rn<=%s ORDER BY c.cd_grupo,c.cd_subgrupo,c.rn""", (known_models, sample_size)).fetchall()
    by_pair = defaultdict(list)
    for item in samples:
        by_pair[(item["cd_grupo"], item["cd_subgrupo"])].append(item)
    counts = {(x["cd_grupo"], x["cd_subgrupo"]): x["count"] for x in inventory}
    if include_unmapped:
        known_pairs = {(r['group_code'], r['subgroup_code']) for r in taxonomy}
        group_names = {r['group_code']: r['group_name'] for r in groups}
        for row in inventory:
            pair = (row['cd_grupo'], row['cd_subgrupo'])
            if pair in known_pairs:
                continue
            group_name = group_names.get(pair[0], f"Grupo ERP {pair[0]} (fora do catalogo ativo)")
            taxonomy.append({'group_code': pair[0], 'subgroup_code': pair[1],
                'group_name': group_name, 'family': row['family'], 'outside_active_catalog': True})
            if pair[0] not in group_names:
                group_names[pair[0]] = group_name
                groups.append({'group_code': pair[0], 'group_name': group_name, 'outside_active_catalog': True})
    cases = []
    for row in taxonomy:
        pair = (row["group_code"], row["subgroup_code"])
        reference = choose_reference(by_pair[pair], catalog)
        cases.append({**row, "id": f"sub-{pair[0]}-{pair[1]}", "level": "subcategory",
                      "initial_message": f"Preciso de {row['family'].lower()}",
                      "source_item_count": counts.get(pair, 0), "reference": reference})
    for row in groups:
        related = [c for c in cases if c["group_code"] == row["group_code"]]
        references = [c["reference"] for c in related if c["reference"]]
        reference = choose_reference(references, catalog)
        family = next((c["family"] for c in related if c["reference"] is reference), row["group_name"])
        cases.append({**row, "id": f"group-{row['group_code']}", "level": "category",
                      "subgroup_code": None, "family": family,
                      "initial_message": f"Preciso de uma peca de {row['group_name'].lower()}",
                      "source_item_count": sum(c["source_item_count"] for c in related), "reference": reference})
    return cases, source, conninfo, errors


class SourceInspector:
    def __init__(self, conninfo, catalog=None):
        self.conninfo = conninfo
        self.catalog = catalog

    def inspect(self, items, case, supplied):
        if not items:
            return []
        ids = [str(x["item_id"]) for x in items]
        with read_connection(self.conninfo) as conn:
            rows = conn.execute("SELECT * FROM soccol.item_search_candidates WHERE cd_item=ANY(%s)", (ids,)).fetchall()
            apps = conn.execute("SELECT * FROM soccol.item_search_applications WHERE id_item=ANY(%s)", ([x["id_item"] for x in rows],)).fetchall()
        by_code = {str(x["cd_item"]): x for x in rows}
        findings = []
        for item in items:
            source = by_code.get(str(item["item_id"]))
            reasons = []
            if not source:
                reasons.append("codigo_ausente_na_fonte")
            elif self.catalog is not None:
                from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor
                from app.infra.pre_search_family_curation import source_identity_matches
                family = DictionaryPreSearchExtractor(catalog=self.catalog).canonicalize_part_query(case['family'])
                accepted = source_identity_matches(source, family, self.catalog) if family else (
                    case['level'] == 'group' and source['cd_grupo'] == case['group_code'])
                if not accepted:
                    reasons.append('fora_da_identidade_curada_solicitada')
            elif source["cd_grupo"] != case["group_code"] or (
                case["level"] == "subcategory" and source["cd_subgrupo"] != case["subgroup_code"]
            ):
                reasons.append("fora_da_categoria_subcategoria_solicitada")
            if source:
                vehicle_facts = {k: supplied[k] for k in ("vehicle_model", "vehicle_brand", "vehicle_year", "engine") if k in supplied}
                if vehicle_facts and not any(application_matches(a, vehicle_facts) for a in apps if a["id_item"] == source["id_item"]):
                    reasons.append("aplicacao_nao_confere_com_dados_respondidos")
                viscosity = supplied.get("variant")
                if norm(case["family"]) == "lubrificantes" and viscosity:
                    m = re.fullmatch(r"(\d{1,2})W(\d{2})", viscosity)
                    if m and not re.search(r"\b"+m[1]+r"\s*w\s*-?\s*"+m[2]+r"\b", norm(source["nm_item"]+" "+source["candidate_title"])):
                        reasons.append("viscosidade_divergente")
            findings.append({**item, "source_group": source["cd_grupo"] if source else None,
                             "source_subgroup": source["cd_subgrupo"] if source else None,
                             "suspicions": reasons})
        return findings


def application_matches(app, facts):
    for field in ("vehicle_model", "vehicle_brand"):
        if field in facts and norm(app.get(field)) != norm(str(facts[field])):
            return False
    if "vehicle_year" in facts:
        year, start, end = int(facts["vehicle_year"]), app.get("year_start"), app.get("year_end")
        if not start or start > year or not (app.get("year_open_end") and end is None or end is not None and end >= year):
            return False
    if "engine" in facts:
        pattern = r"(?<![\w.])" + re.escape(str(facts["engine"])) + r"(?![\w.])"
        if not any(re.search(pattern, str(x), re.I) for x in app.get("engines") or []):
            return False
    return True


class RecordingTools:
    def __init__(self, actual):
        self.actual = actual
        self.searches = []

    def resolve_follow_up_value(self, **kwargs):
        return self.actual.resolve_follow_up_value(**kwargs)

    def search_parts(self, query, branch_id, criteria=None):
        items = self.actual.search_parts(query, branch_id, criteria)
        self.searches.append({"criteria": criteria.model_dump(exclude_none=True) if criteria else {},
                              "returned_ids": [x.item_id for x in items],
                              "products": [x.model_dump(mode='json') for x in items],
                              "diagnostics": self.get_last_search_diagnostics()})
        return items

    def get_last_search_diagnostics(self):
        getter = getattr(self.actual, "get_last_search_diagnostics", None)
        return getter() if callable(getter) else None


def displayed_items(body, searches):
    """Single-item confirmations can be public text without show_items actions."""
    data = normalize_response(body)
    found = {str(i['item_id']): {**i, 'presentation_origin': 'show_items'} for i in data['catalog_candidates']}
    for result in body.get('item_results') or []:
        for item in result.get('products') or []:
            found.setdefault(str(item['item_id']), {**item, 'presentation_origin': 'item_results'})
    actual = {}
    for search in searches:
        candidates = search.get('products') or (search.get('diagnostics') or {}).get('ranked_candidates') or []
        allowed = set(search.get('returned_ids') or [])
        for item in candidates:
            if str(item.get('item_id')) in allowed:
                actual[str(item['item_id'])] = item
    for match in re.finditer(r'\(c[oó]digo\s+([^\)]+)\)', data['reply_text'], re.I):
        code = match[1].strip()
        if code in actual:
            item = actual[code]
            found.setdefault(code, {'item_id': code, 'title': item.get('title', ''),
                'score': item.get('score', item.get('raw_score')), 'presentation_origin': 'reply_confirmation'})
    return [{'position': index, **item} for index, item in enumerate(found.values(), 1)]


def answer_question(case, state, actions, supplied):
    facts = reference_facts(case.get("reference"))
    key = state.get("pending_slot")
    question = next((a for a in actions if a.get("type") == "request_info"), {})
    key = key or question.get("key")
    disambiguation = state.get("result_disambiguation") or {}
    if disambiguation:
        code = (case.get("reference") or {}).get("cd_item")
        for option in disambiguation.get("options") or []:
            if code in option.get("candidate_ids", []):
                return option["label"], "opcao_contem_item_de_referencia", None
        if code in [x.get("item_id") for x in disambiguation.get("candidates", [])]:
            return code, "codigo_presente_nos_candidatos", None
        return None, "desambiguacao_sem_opcao_comprovada_pela_referencia", None
    if key == "part_query":
        if case.get('generic_family') and case.get('reference'):
            return case['reference']['candidate_title'], "descricao_do_item_de_referencia", None
        return case["family"].lower(), "subcategoria_do_catalogo", None
    if key in facts:
        supplied[key] = facts[key]
        return str(facts[key]), "dado_do_item_ou_mesma_aplicacao", key
    if key in {"vehicle_model", "vehicle_year", "engine", "side", "position", "axle", "variant", "coxim_type"}:
        return "nao sei", "referencia_sem_dado_para_responder", None
    return None, "pergunta_sem_resposta_comprovada", None


class EvaluationUseCase(ProcessAgentRequestUseCase):
    """Evaluation scheduling only; leave production use-case code unchanged.

    The production validator semaphore also guards deterministic calls.
    Separately queue residual inference here so slow cases do not hold the
    entire coverage battery. This run must not be used as a load benchmark.
    """
    async def _run_validator_call(self, function, /, *args, **kwargs):
        if getattr(function, '__name__', '') == 'validate':
            async with self.inference_limit:
                return await super()._run_validator_call(function, *args, **kwargs)
        return await super()._run_validator_call(function, *args, **kwargs)


async def run_case(case, settings, catalog, inspector, max_turns, shared_limits=None):
    logger = logging.getLogger("category-search")
    tools = RecordingTools(resolve_search_tools(settings=settings, logger=logger, catalog=catalog))
    use_case = EvaluationUseCase(tools=tools,
        pre_search_validator=LLMPreSearchValidator(settings=settings, logger=logger, catalog=catalog),
        settings=settings, logger=logger, review_recorder=NoOpPreSearchReviewRecorder())
    # Mirror a single server's global resource limits across isolated cases.
    # Waiting for LLM capacity must not occupy executor threads or block cases
    # that can be completed deterministically.
    use_case.inference_limit = shared_limits[0] if shared_limits else asyncio.Semaphore(1)
    if shared_limits:
        use_case._erp_search_semaphore = shared_limits[1]
    state, history, supplied, turns, repeated = None, [], dict(case.get('initial_facts', {})), [], set()
    conversation_id = f"coverage-{case['id']}-{uuid.uuid4().hex[:8]}"
    message = case["initial_message"]
    response_basis = "pergunta_inicial_por_categoria"
    stop = "limite_de_turnos"
    returned = []
    for index in range(max_turns):
        payload = AgentRequestV1(schema_version="1.0", trace_id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            channel={"name": "category-coverage-eval"}, message={"text": message},
            business={"branch_id": 1}, context={"last_messages": history[-20:], "conversation_state": state})
        started = time.monotonic()
        try:
            result = await use_case.execute(payload)
            body = result.model_dump(mode="json")
            normalized = normalize_response(body)
        except Exception as exc:
            turns.append({"user": message, "error_type": type(exc).__name__, "latency_s": round(time.monotonic()-started, 2)})
            stop = "erro_operacional"
            break
        state = normalized["conversation_state"]
        items = displayed_items(body, tools.searches)
        returned.extend(await asyncio.to_thread(inspector.inspect, items, case, supplied))
        turns.append({"user": message, "answer_basis": response_basis, "assistant": normalized["reply_text"],
                      "latency_s": round(time.monotonic()-started, 2), "response": body})
        history += [{"role": "user", "text": message}, {"role": "assistant", "text": normalized["reply_text"]}]
        if items:
            stop = "itens_apresentados"
            break
        if normalized["handoff_required"]:
            stop = "encaminhamento_humano"
            break
        message, response_basis, _ = answer_question(case, state, normalized["actions"], supplied)
        if not message:
            stop = response_basis
            break
        signature = (state.get("pending_slot"), message)
        if signature in repeated:
            stop = "pergunta_repetida"
            break
        repeated.add(signature)
    reference = case.get("reference")
    reference_consistent = bool(reference) and application_matches(reference.get("application") or {},
        {k: v for k, v in supplied.items() if k in {"vehicle_model", "vehicle_brand", "vehicle_year", "engine"}})
    if returned:
        verdict = "suspeita_item_incorreto" if any(x["suspicions"] for x in returned) else "itens_coerentes_com_cadastro"
    elif stop == "erro_operacional":
        verdict = "erro_operacional"
    elif case["source_item_count"] == 0:
        verdict = "sem_itens_na_subcategoria_fonte"
    elif reference_consistent and any(s["returned_ids"] == [] for s in tools.searches):
        verdict = "suspeita_falso_negativo"
    elif stop == "encaminhamento_humano" and any(t.get("answer_basis") == "referencia_sem_dado_para_responder" for t in turns):
        verdict = "handoff_por_dado_desconhecido"
    else:
        verdict = "nao_concluiu_busca_com_itens_na_fonte"
    return {**case, "turns": turns, "items": returned, "supplied_facts": supplied,
            "searches": tools.searches, "stop_reason": stop, "verdict": verdict,
            "reference_consistent_with_answers": reference_consistent, "human_review_required": True}


def write_reports(directory, metadata, results):
    counts = dict(Counter(x["verdict"] for x in results))
    labels = {
        'itens_coerentes_com_cadastro': 'Itens coerentes com o cadastro',
        'suspeita_item_incorreto': 'Suspeita de item inadequado',
        'suspeita_falso_negativo': 'Busca vazia: revisar possivel falso negativo',
        'handoff_por_dado_desconhecido': 'Encaminhamento: dado solicitado desconhecido',
        'sem_itens_na_subcategoria_fonte': 'Sem itens na subcategoria da fonte',
        'nao_concluiu_busca_com_itens_na_fonte': 'Nao apresentou itens, apesar de haver cadastro',
        'erro_operacional': 'Erro operacional',
    }
    report = {"metadata": metadata, "summary": {"completed": len(results), "verdicts": counts}, "results": results}
    (directory/"report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for case in results:
        reference = case.get('reference') or {}
        content = [f"Pergunta: {case['initial_message']}", f"Itens na fonte: {case['source_item_count']}",
                   f"Referencia: {reference.get('cd_item', 'sem referencia')} - {reference.get('candidate_title', '')}",
                   "Aplicacao da referencia: " + json.dumps(reference.get('application'), ensure_ascii=False),
                   "Dados respondidos: " + json.dumps(case.get('supplied_facts', {}), ensure_ascii=False),
                   "Parada: " + case.get('stop_reason', '')]
        if re.match(r"^(kit|reparo|suporte|tampa|mangueira)\b", norm(reference.get('candidate_title'))):
            content.append("ATENCAO: referencia e acessorio/conjunto; nao prova existencia da peca principal solicitada.")
        for turn in case["turns"]:
            content.extend(["Cliente: "+turn["user"], "Bot: "+turn.get("assistant", turn.get("error_type", ""))])
        for search in case.get('searches', []):
            content.extend(['Filtros enviados ao ERP: ' + json.dumps(search.get('criteria', {}), ensure_ascii=False),
                            'Codigos retornados pela busca: ' + ', '.join(search.get('returned_ids') or [])])
        if case.get('criteria_differences'):
            content.append('ATENCAO: filtros diferem dos dados fornecidos: ' + json.dumps(case['criteria_differences'], ensure_ascii=False))
        if case.get('outside_active_catalog'):
            content.append('ATENCAO: grupo/subgrupo da fonte ausente do catalogo ativo.')
        content.extend([f"{i['item_id']} - {i['title']} | suspeitas: {', '.join(i['suspicions']) or 'nenhuma estrutural'}" for i in case["items"]])
        rows.append(f"<tr><td>{html.escape(case['id'])}</td><td>{html.escape(case['group_name'])}</td><td>{html.escape(case['family'])}</td><td title='{html.escape(case['verdict'])}'>{html.escape(labels.get(case['verdict'], case['verdict']))}</td><td><details><summary>{len(case['turns'])} turnos / {len(case['items'])} itens</summary><pre>{html.escape(chr(10).join(content))}</pre></details></td></tr>")
    page = """<!doctype html><meta charset="utf-8"><title>Cobertura de categorias do bot</title>
    <style>body{font:15px system-ui;margin:28px;background:#f7f8fa;color:#172033}table{border-collapse:collapse;width:100%;background:white}td,th{padding:10px;border:1px solid #dde2ea;text-align:left;vertical-align:top}pre{white-space:pre-wrap;min-width:400px}input{padding:10px;width:50%}</style>
    <h1>Cobertura por categoria/subcategoria</h1><p>Uma conversa por entrada. Coerencia com cadastro nao certifica encaixe comercial nem cobertura de todos os produtos. Avaliacao assistida, sujeita a revisao humana.</p>
    <input placeholder="Filtrar categoria, resultado ou codigo" oninput="document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase()))">
    """+f"<p>{len(results)} de {metadata.get('planned_cases', len(results))} conversas registradas.</p><ul>"+''.join(f"<li>{html.escape(labels.get(key, key))}: {value}</li>" for key,value in counts.items())+"</ul><table><thead><tr><th>ID</th><th>Categoria</th><th>Subcategoria</th><th>Avaliacao</th><th>Conversa e produtos</th></tr></thead><tbody>"+"".join(rows)+"</tbody></table>"
    (directory/"report.html").write_text(page, encoding="utf-8")
    lines = ["# Cobertura de categorias/subcategorias", "", json.dumps(metadata, ensure_ascii=False), "", "| Caso | Categoria | Subcategoria | Resultado | Itens |", "|---|---|---|---|---|"]
    lines += [f"| {c['id']} | {c['group_name']} | {c['family']} | {c['verdict']} | {', '.join(i['item_id'] for i in c['items'])} |" for c in results]
    (directory/"report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


async def main_async(args):
    settings = Settings().model_copy(update={"pre_search_review_capture_enabled": False, "llm_warmup_enabled": False})
    logging.basicConfig(level=logging.ERROR)
    catalog = resolve_pre_search_catalog(settings=settings, logger=logging.getLogger("coverage"))
    if args.resume_dir:
        directory = args.resume_dir
        previous = json.loads((directory/'report.json').read_text(encoding='utf-8'))
        cases = json.loads((directory/'cases.json').read_text(encoding='utf-8'))
        source = previous['metadata']['source']
        conninfo = build_erp_conninfo(settings) if source == 'erp_postgres' else build_catalog_conninfo(settings)
        results = previous['results']
        metadata = previous['metadata']
        if args.retry_errors:
            retried = [r for r in results if r['verdict'] == 'erro_operacional']
            metadata.setdefault('previous_error_attempts', []).extend(retried)
            results = [r for r in results if r['verdict'] != 'erro_operacional']
        metadata.setdefault('resumptions', []).append({'at': datetime.now(timezone.utc).isoformat(),
            'completed_before_resume': len(results), 'case_concurrency': args.concurrency,
            'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        completed = {r['id'] for r in results}
        pending = [c for c in cases if c['id'] not in completed]
    else:
        cases, source, conninfo, errors = await asyncio.to_thread(prepare_cases, settings, catalog, args.samples, args.include_unmapped_source)
        if args.reference_queries:
            for case in cases:
                case['category_label_prompt'] = case['initial_message']
                case['initial_message'], case['initial_facts'] = reference_query(case, catalog)
                case['generic_family'] = norm(case['family']) in catalog.generic_ambiguous_parts
        results = []
        pending = cases
    if args.case_id and not args.resume_dir:
        cases = [c for c in cases if c["id"] in args.case_id]
    if args.limit and not args.resume_dir:
        cases = cases[:args.limit]
    if not args.resume_dir:
        pending = cases
        directory = args.output_dir or Path(".tmp/eval/category_search")/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        directory.mkdir(parents=True, exist_ok=False)
        metadata = {"execution_mode": "isolated_current_checkout_use_case", "source": source,
                "source_probe_errors": errors, "model": settings.llm_model, "planned_cases": len(cases),
                "created_at": datetime.now(timezone.utc).isoformat(), "samples_per_subcategory": args.samples,
                "max_turns": args.max_turns, "capture_to_training_queue": False,
                "query_mode": "reference_assisted" if args.reference_queries else "category_label_only",
                "interpretation": "source-consistency screening; human review required; not full inventory recall",
                "code_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path('app/infra/erp_search_query.py'),Path('app/infra/pre_search_dictionary_extractor.py')]}}
        (directory/"cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    write_reports(directory, metadata, results)
    inspector, semaphore = SourceInspector(conninfo, catalog), asyncio.Semaphore(args.concurrency)
    shared_limits = (asyncio.Semaphore(max(1, min(2, settings.llm_max_concurrent_requests))),
                     asyncio.Semaphore(max(1, min(4, settings.erp_search_max_concurrent_requests))))
    async def one(case):
        async with semaphore:
            result = await run_case(case, settings, catalog, inspector, args.max_turns, shared_limits)
            results.append(result)
            results.sort(key=lambda x: x["id"])
            write_reports(directory, metadata, results)
            print(json.dumps({"progress": f"{len(results)}/{len(cases)}", "case": case["id"], "verdict": result["verdict"], "turns": len(result["turns"]), "items": len(result["items"])}, ensure_ascii=False), flush=True)
    await asyncio.gather(*(one(c) for c in pending))
    metadata['finished_at'] = datetime.now(timezone.utc).isoformat()
    write_reports(directory, metadata, results)
    print(json.dumps({"report": str(directory), "summary": dict(Counter(c["verdict"] for c in results))}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--resume-dir", type=Path)
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--reference-queries", action="store_true")
    parser.add_argument("--include-unmapped-source", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--concurrency", type=int, choices=[1,2,4,8,16,32], default=4)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
