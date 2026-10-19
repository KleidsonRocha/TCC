from scripts.eval.evaluate_category_search import application_matches, answer_question, reference_facts, write_reports
import json
import asyncio
from types import SimpleNamespace


def test_reference_question_supplies_known_facts_without_using_item_code():
    from scripts.eval.evaluate_category_search import reference_query
    catalog = SimpleNamespace(part_patterns=[('radiador', ('radiador',))], generic_ambiguous_parts=set())
    case = {'family': 'RADIADOR', 'reference': {'cd_item': 'SECRET-CODE', 'nm_item': 'RADIADOR',
        'application': {'vehicle_model': 'Gol', 'vehicle_brand': 'Volkswagen',
                        'year_start': 2008, 'year_end': 2012, 'engines': ['1.0 L 8V']}}}
    message, facts = reference_query(case, catalog)
    assert 'SECRET-CODE' not in message
    assert 'Gol 2010 motor 1.0' in message
    assert facts == {'vehicle_model': 'Gol', 'vehicle_year': '2010', 'engine': '1.0'}


def test_inference_queue_does_not_block_deterministic_checks(monkeypatch):
    from scripts.eval.evaluate_category_search import EvaluationUseCase, ProcessAgentRequestUseCase
    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()
        active = peak = 0
        async def fake_call(self, function, *args, **kwargs):
            nonlocal active, peak
            if function.__name__ == 'validate':
                active += 1
                peak = max(peak, active)
                entered.set()
                await release.wait()
                active -= 1
            return function.__name__
        monkeypatch.setattr(ProcessAgentRequestUseCase, '_run_validator_call', fake_call)
        def validate():
            pass
        def deterministic():
            pass
        first, second = EvaluationUseCase.__new__(EvaluationUseCase), EvaluationUseCase.__new__(EvaluationUseCase)
        first.inference_limit = second.inference_limit = asyncio.Semaphore(1)
        a = asyncio.create_task(first._run_validator_call(validate))
        b = asyncio.create_task(second._run_validator_call(validate))
        await entered.wait()
        assert await second._run_validator_call(deterministic) == 'deterministic'
        release.set()
        assert await asyncio.gather(a, b) == ['validate', 'validate']
        assert peak == 1
    asyncio.run(exercise())


def test_reference_uses_one_application_and_does_not_invent_universal_vehicle():
    assert reference_facts({"part_family": "lubrificantes", "nm_item": "OLEO 5W-40", "application": {
        "vehicle_model": "TODOS", "vehicle_brand": "TODOS", "year_start": 1926,
        "variants": ["TODOS"], "engines": [],
    }}) == {"variant": "5W40"}


def test_source_application_requires_model_year_and_engine_together():
    facts = {"vehicle_model": "Gol", "vehicle_year": "2010", "engine": "1.0"}
    old_gol = {"vehicle_model": "Gol", "year_start": 1995, "year_end": 1999, "engines": ["1.0"]}
    new_fox = {"vehicle_model": "Fox", "year_start": 2008, "year_end": 2012, "engines": ["1.0"]}
    assert not application_matches(old_gol, facts)
    assert not application_matches(new_fox, facts)
    assert application_matches({**new_fox, "vehicle_model": "Gol"}, facts)
    assert not application_matches({**new_fox, "vehicle_model": "Gol", "engines": ["11.0"]}, facts)


def test_unknown_attribute_answers_dont_choose_arbitrary_options():
    case = {"family": "radiador", "reference": {"nm_item": "RADIADOR", "application": {}}}
    supplied = {}
    reply, basis, field = answer_question(case, {"pending_slot": "engine"}, [
        {"type": "request_info", "key": "engine", "options": ["1.0", "1.6"]}
    ], supplied)
    assert reply == "nao sei"
    assert supplied == {}


def test_single_item_confirmation_is_preserved_without_structured_action():
    from scripts.eval.evaluate_category_search import displayed_items
    body = {'reply_text': 'Encontrei OLEO 5W40 (codigo TEX-3117).', 'actions': []}
    searches = [{'returned_ids': ['TEX-3117'], 'diagnostics': {'ranked_candidates': [
        {'item_id': 'TEX-3117', 'title': 'OLEO 5W40', 'raw_score': 0.5}
    ]}}]
    assert displayed_items(body, searches)[0]['item_id'] == 'TEX-3117'
    assert displayed_items(body, searches)[0]['presentation_origin'] == 'reply_confirmation'
    assert displayed_items({'reply_text': '(codigo INVENTADO)', 'actions': []}, searches) == []


def test_disambiguation_only_selects_option_containing_reference():
    case = {"family": "radiador", "reference": {"cd_item": "REF"}}
    state = {"result_disambiguation": {"options": [
        {"label": "errada", "candidate_ids": ["OTHER"]}, {"label": "correta", "candidate_ids": ["REF"]}
    ]}}
    assert answer_question(case, state, [], {})[0] == "correta"
    state["result_disambiguation"]["options"] = state["result_disambiguation"]["options"][:1]
    assert answer_question(case, state, [], {})[0] is None


def test_reports_preserve_conversation_and_item_codes_and_escape_html(tmp_path):
    case = {"id": "sub-1-1", "group_name": "Grupo", "family": "<Familia>",
            "initial_message": "Preciso", "source_item_count": 1, "reference": {"cd_item": "REF"},
            "verdict": "itens_coerentes_com_cadastro", "turns": [{"user": "Gol", "assistant": "Resposta"}],
            "items": [{"item_id": "REF", "title": "Produto", "suspicions": []}]}
    write_reports(tmp_path, {"planned_cases": 1}, [case])
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["results"][0]["items"][0]["item_id"] == "REF"
    page = (tmp_path / "report.html").read_text()
    assert "&lt;Familia&gt;" in page and "Cliente: Gol" in page and "REF - Produto" in page


def test_consolidation_recovers_confirmed_item_and_preserves_original_judgment(tmp_path, monkeypatch):
    from scripts.eval import consolidate_category_search as module
    run = tmp_path / 'run'
    run.mkdir()
    case = {'id': 'sub-1-1', 'level': 'subcategory', 'group_name': 'Grupo',
            'family': 'Familia', 'initial_message': 'Preciso', 'source_item_count': 1}
    (run / 'cases.json').write_text(json.dumps([case]))
    row = {**case, 'items': [], 'supplied_facts': {},
        'verdict': 'nao_concluiu_busca_com_itens_na_fonte', 'stop_reason': 'pergunta_sem_resposta_comprovada',
        'turns': [{'user': 'Preciso', 'assistant': 'Encontrei (codigo REF)',
                   'response': {'reply_text': 'Encontrei (codigo REF)', 'actions': []}}],
        'searches': [{'returned_ids': ['REF'], 'products': [{'item_id': 'REF', 'title': 'Produto'}]}]}
    (run / 'report.json').write_text(json.dumps({'metadata': {'source': 'erp_postgres', 'finished_at': 'now'}, 'results': [row]}))
    monkeypatch.setattr(module, 'build_erp_conninfo', lambda settings: 'unused')
    monkeypatch.setattr(module.SourceInspector, 'inspect', lambda self, items, case, supplied: [{**i, 'suspicions': []} for i in items])
    output = tmp_path / 'output'
    module.consolidate([run], output)
    report = json.loads((output / 'report.json').read_text())
    result = report['results'][0]
    assert result['items'][0]['item_id'] == 'REF'
    assert result['verdict'] == 'itens_coerentes_com_cadastro'
    assert result['before_reconciliation']['verdict'] == row['verdict']
    assert report['metadata']['reconciled_single_item_confirmations'] == ['sub-1-1']


def test_consolidation_rejects_unfinished_run(tmp_path):
    import pytest
    from scripts.eval.consolidate_category_search import consolidate
    (tmp_path / 'cases.json').write_text(json.dumps([{'id': 'pending'}]))
    (tmp_path / 'report.json').write_text(json.dumps({'metadata': {}, 'results': []}))
    with pytest.raises(ValueError, match='not complete'):
        consolidate([tmp_path], tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_criteria_differences_separate_extraction_drift_from_empty_search():
    from scripts.eval.consolidate_category_search import criteria_differences
    row = {'supplied_facts': {'vehicle_model': 'Sandero', 'vehicle_year': '2010'},
           'searches': [{'criteria': {'vehicle_model': 'SANDERO', 'vehicle_year': 2007}}]}
    assert criteria_differences(row) == [{'search': 1, 'field': 'vehicle_year', 'provided': '2010', 'used': 2007}]


def test_partial_consolidation_does_not_claim_completion(tmp_path):
    from scripts.eval.consolidate_category_search import consolidate
    run = tmp_path / 'run'
    run.mkdir()
    case = {'id': 'pending', 'level': 'category', 'group_name': 'Grupo', 'family': 'Familia', 'initial_message': 'Preciso'}
    (run / 'cases.json').write_text(json.dumps([case]))
    (run / 'report.json').write_text(json.dumps({'metadata': {'source': 'erp_postgres'}, 'results': []}))
    output = tmp_path / 'output'
    consolidate([run], output, allow_partial=True)
    report = json.loads((output / 'report.json').read_text())
    assert report['metadata']['finished_at'] is None
    assert report['metadata']['report_status'] == 'partial'
    assert report['metadata']['planned_cases'] == 1
    assert report['summary']['completed'] == 0
    assert 'pending' in (output / 'questions.md').read_text()
    result = {**case, 'source_item_count': 0, 'items': [], 'turns': [], 'searches': [],
              'supplied_facts': {}, 'verdict': 'sem_itens_na_subcategoria_fonte', 'stop_reason': 'done'}
    (run / 'report.json').write_text(json.dumps({'metadata': {'source': 'erp_postgres', 'finished_at': 'now'}, 'results': [result]}))
    consolidate([run], output, replace_output=True)
    final = json.loads((output / 'report.json').read_text())
    assert final['metadata']['report_status'] == 'complete'
    assert final['metadata']['finished_at']
    assert final['summary']['completed'] == 1
