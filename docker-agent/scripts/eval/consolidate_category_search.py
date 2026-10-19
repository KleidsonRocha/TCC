"""Consolidate finished coverage runs and reconcile single-item confirmations.

Only codes both publicly confirmed and returned by the recorded search count.
Newly recovered products are independently checked against the read-only source.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from app.config import Settings
from app.infra.postgres_conninfo import build_catalog_conninfo, build_erp_conninfo
from scripts.eval.evaluate_category_search import SourceInspector, displayed_items, write_reports
from app.infra.pre_search_text import normalize_pre_search_text as norm


def criteria_differences(row):
    differences = []
    for index, search in enumerate(row.get('searches', []), 1):
        criteria = search.get('criteria') or {}
        for field in ('vehicle_model', 'vehicle_brand', 'vehicle_year', 'engine'):
            provided = row.get('supplied_facts', {}).get(field)
            used = criteria.get(field)
            if provided is not None and used is not None and norm(str(provided)) != norm(str(used)):
                differences.append({'search': index, 'field': field, 'provided': provided, 'used': used})
    return differences


def consolidate(directories, output, *, allow_partial=False, replace_output=False):
    cohorts, cases, results, reconciled = [], [], [], []
    settings = Settings()
    for directory in directories:
        report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
        planned = json.loads((directory / 'cases.json').read_text(encoding='utf-8'))
        metadata = report['metadata']
        complete = bool(metadata.get('finished_at')) and {r['id'] for r in report['results']} == {c['id'] for c in planned}
        if not complete and not allow_partial:
            raise ValueError(f'Coverage run is not complete: {directory}')
        cohorts.append({'directory': str(directory), 'metadata': metadata})
        conninfo = build_erp_conninfo(settings) if metadata['source'] == 'erp_postgres' else build_catalog_conninfo(settings)
        inspector = SourceInspector(conninfo)
        cases.extend(planned)
        for row in report['results']:
            row['criteria_differences'] = criteria_differences(row)
            existing = {str(i['item_id']) for i in row['items']}
            recovered = {}
            for turn in row['turns']:
                if turn.get('response'):
                    for item in displayed_items(turn['response'], row['searches']):
                        code = str(item['item_id'])
                        if code not in existing:
                            recovered[code] = item
            if recovered:
                row['before_reconciliation'] = {'verdict': row['verdict'], 'stop_reason': row['stop_reason']}
                row['items'].extend(inspector.inspect(list(recovered.values()), row, row['supplied_facts']))
                row['verdict'] = 'suspeita_item_incorreto' if any(i['suspicions'] for i in row['items']) else 'itens_coerentes_com_cadastro'
                row['stop_reason'] = 'itens_confirmados_no_texto'
                reconciled.append(row['id'])
            results.append(row)
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Duplicate cases across coverage runs')
    results.sort(key=lambda r: r['id'])
    metadata = {
        'execution_mode': 'isolated_current_checkout_use_case',
        'planned_cases': len(cases),
        'category_cases': sum(c['level'] == 'category' for c in cases),
        'subcategory_cases': sum(c['level'] == 'subcategory' for c in cases),
        'finished_at': None if allow_partial else datetime.now(timezone.utc).isoformat(),
        'report_status': 'partial' if allow_partial else 'complete',
        'cohorts': cohorts,
        'reconciled_single_item_confirmations': reconciled,
        'consolidator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'checker_sha256': hashlib.sha256(Path('scripts/eval/evaluate_category_search.py').read_bytes()).hexdigest(),
        'interpretation': 'Source-consistency screening; human review required; one conversation per entry, not full inventory recall.',
        'checks': ['source code exists', 'source group/subgroup', 'same application model/brand/year/engine', 'oil viscosity'],
        'limitations': ['No physical compatibility certification', 'No independent side/position/vehicle-variant verification', 'No gateway/WhatsApp transport test', 'References are frozen per run; live ERP data is not snapshot-locked across resumptions'],
    }
    if output.exists() and replace_output:
        previous = json.loads((output / 'report.json').read_text(encoding='utf-8'))
        if 'consolidator_sha256' not in previous['metadata']:
            raise ValueError('Refusing to replace an output not created by this consolidator')
    else:
        output.mkdir(parents=True, exist_ok=False)
    (output / 'cases.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')
    questions = ['# Perguntas da auditoria', '',
        'Uma conversa por categoria/subcategoria. A referencia demonstra cadastro; nao e gabarito exclusivo nem certificacao de compatibilidade.', '']
    for case in cases:
        reference = case.get('reference') or {}
        questions.extend([f"## {case['id']} - {case['group_name']} / {case['family']}", '',
            case['initial_message'], '',
            f"Referencia: {reference.get('cd_item', 'sem item na fonte')} - {reference.get('candidate_title', '')}", ''])
    (output / 'questions.md').write_text('\n'.join(questions), encoding='utf-8')
    write_reports(output, metadata, results)
    print(json.dumps({'output': str(output), 'completed': len(results), 'reconciled': len(reconciled)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, action='append', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--watch', action='store_true', help='Write a partial report, then replace it when every input run finishes')
    args = parser.parse_args()
    if not args.watch:
        consolidate(args.run_dir, args.output_dir)
        return
    consolidate(args.run_dir, args.output_dir, allow_partial=True)
    while True:
        try:
            reports = [json.loads((directory / 'report.json').read_text(encoding='utf-8')) for directory in args.run_dir]
        except json.JSONDecodeError:
            # The evaluator may be in the middle of writing a checkpoint.
            time.sleep(5)
            continue
        if all(report['metadata'].get('finished_at') for report in reports):
            consolidate(args.run_dir, args.output_dir, replace_output=True)
            break
        time.sleep(10)


if __name__ == '__main__':
    main()
