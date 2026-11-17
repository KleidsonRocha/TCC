"""Verify the evidence and recalculate archived results without network or GPU.

Requires Python >= 3.11, standard library only. Writes only to a NEW output
directory; never overwrites the published evidence or an earlier recalculation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

EVIDENCE = Path(__file__).resolve().parents[1]
REPOSITORY = EVIDENCE.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify():
    manifest = read(EVIDENCE / 'MANIFESTO.json')
    for name, expected in manifest['files'].items():
        path = (EVIDENCE / name).resolve()
        if not path.is_relative_to(EVIDENCE):
            raise ValueError('Manifest path escapes evidence directory')
        if not path.is_file() or digest(path) != expected['sha256'] or path.stat().st_size != expected['bytes']:
            raise ValueError(f'File missing or altered: {name}')
    counts = {}
    for name in ['01_tecnico.zip', '02_rubricas.zip', '03_fine_tuning/registros_20261019.zip']:
        with zipfile.ZipFile(EVIDENCE / name) as z:
            if z.testzip() is not None:
                raise ValueError(f'Archive corrupted: {name}')
            if len(set(z.namelist())) != len(z.namelist()):
                raise ValueError(f'Duplicate archive paths: {name}')
            counts[name] = len(z.namelist())
    with zipfile.ZipFile(EVIDENCE / '01_tecnico.zip') as z:
        cases = [name for name in z.namelist() if name.startswith('tecnico/runs/') and name.endswith('.json')]
        if len(cases) != 3408:
            raise ValueError('Expected exactly 3408 official case records')
        for entry in read(EVIDENCE / 'VERSAO_EXPERIMENTAL.json')['files']:
            prefix, rel = entry['path'].split('/', 1)
            folder = 'frozen' if prefix == 'docker-agent' else 'gateway_frozen'
            member = f'tecnico/{folder}/{rel}'
            if member in z.namelist() and hashlib.sha256(z.read(member)).hexdigest() != entry['frozen_sha256']:
                raise ValueError(f'Frozen source altered: {member}')
    return {'files_verified': len(manifest['files']), 'archives': counts, 'official_case_records': len(cases)}


def extract(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination) or ':' in member.filename or '\\' in member.filename:
                raise ValueError('Unsafe archive path')
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(member))


def execute(script, *arguments, cwd=None):
    return subprocess.run([sys.executable, '-X', 'utf8', str(script), *map(str, arguments)],
                          cwd=cwd, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                          text=True, encoding='utf-8', capture_output=True, check=True)


def without_generated(value):
    if isinstance(value, dict):
        return {k: without_generated(v) for k, v in value.items() if k not in {'generated_at', 'generated_at_utc'}}
    if isinstance(value, list):
        return [without_generated(v) for v in value]
    return value


def recalculate(output, include_rubrics=False):
    output = output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory; previous results are preserved')
    if output.is_relative_to(EVIDENCE):
        raise ValueError('Choose output outside the published evidence directory')
    output.mkdir(parents=True)
    status = {'integrity': verify()}
    # Table 5: execute the original comparison with its original relative inputs.
    work = output / 'tabela_5'
    (work / '.tmp').mkdir(parents=True)
    for name in ['deterministic_ask_baseline_50.json', 'deterministic_ask_enabled_50.json']:
        shutil.copyfile(EVIDENCE / '05_desempenho' / name, work / '.tmp' / name)
    result = execute(EVIDENCE / '05_desempenho/compare_deterministic_ask.py', cwd=work)
    measured = json.loads(result.stdout)
    (work / 'metricas.json').write_text(result.stdout, encoding='utf-8')
    assert measured['baseline_paths']['llm'] == 31 and measured['enabled_paths']['llm'] == 12
    status['table_5'] = measured
    # Table 6: exact original evaluator, annotations and paired captured outputs.
    work = output / 'tabela_6'
    work.mkdir()
    ranking = EVIDENCE / '04_ranking'
    execute(ranking / 'evaluate_real_ranking.py', '--run', ranking / 'real_respond_battery_comm_20260929T125748400473Z.json',
            '--compare-run', ranking / 'bateria_ranking_atual.json', '--annotations',
            ranking / 'real_respond_ranking_annotations_v1.json', '--output', work / 'comparacao_ranking.md')
    assert (work / 'comparacao_ranking.md').read_bytes().replace(b'\r\n', b'\n') == (ranking / 'comparacao_ranking.md').read_bytes().replace(b'\r\n', b'\n')
    status['table_6_report_matches'] = True
    # Tables 8-9: original aggregator and all four recorded report.json inputs.
    work = output / 'tabelas_8_9'
    extract(EVIDENCE / '03_fine_tuning/registros_20261019.zip', work)
    expected = read(work / 'comparison_summary.json')
    execute(work / 'aggregate.py', cwd=work)
    actual = read(work / 'comparison_summary.json')
    assert without_generated(expected) == without_generated(actual), 'Fine-tuning metrics differ'
    status['tables_8_9_match'] = True
    # Table 10: all 3408 cases; writes the recalculation into the NEW copy.
    work = output / 'ablacao'
    extract(EVIDENCE / '01_tecnico.zip', work)
    study = work / 'tecnico'
    expected = read(study / 'summary.json')
    execute(study / 'analysis/aggregate_results.py', cwd=study)
    actual = read(study / 'summary.json')
    assert without_generated(expected) == without_generated(actual), 'Final ablation metrics differ'
    status['table_10_matches'] = True
    # Table 11 can always be recounted from the three archived auxiliary labels.
    # Re-executing the rules uses the exact separately published 19/10 snapshot.
    work = output / 'rubricas'
    extract(EVIDENCE / '02_rubricas.zip', work)
    key = read(work / 'chave_configuracoes.json')['cases']
    from collections import Counter
    counted = []
    for name in sorted(work.glob('avaliacao_IA_*_V3.json')):
        review = read(name)
        assert len(review['assessments']) == 371
        for arm in ['D', 'H']:
            totals = Counter()
            for cid, item in review['assessments'].items():
                label = next(label for label, value in key[cid]['arms'].items() if value == arm)
                totals[item[label]['overall']] += 1
            counted.append({'persona': review['reviewer_id'], 'arm': arm, 'n': 371, **dict(totals)})
    archived = read(work / 'metricas_por_configuracao.json')['counts']
    for row in counted:
        ref = next(r for r in archived if r['scope'] == 'all_371' and r['persona'] == row['persona'] and r['arm'] == row['arm'])
        assert all(row.get(k, 0) == ref.get(k, 0) for k in ['adequate', 'partly', 'inadequate', 'unknown'])
    (work / 'recontagem_tabela_11.json').write_text(json.dumps(counted, ensure_ascii=False, indent=2), encoding='utf-8')
    status['table_11_recount_matches'] = True
    if include_rubrics:
        scripts = output / 'reexecucao_rubricas'
        shutil.copytree(EVIDENCE / 'reproducao/rubricas', scripts)
        shutil.copyfile(work / 'reproducao/criterios_prioritarios.json', scripts / 'criterios_prioritarios.json')
        shutil.copytree(study, scripts / 'tecnico')
        snapshot = scripts / 'tecnico/inputs/source_snapshot'
        source_manifest = read(snapshot / 'manifest.json')
        for name in ['candidates.csv.gz', 'applications.csv.gz']:
            src = EVIDENCE / 'catalogo_20261019' / name
            if not src.is_file() or digest(src) != source_manifest['files'][name]['sha256']:
                raise ValueError(f'Experimental 19/10 snapshot missing or differs: {name}')
            shutil.copyfile(src, snapshot / name)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'EVAL_SOURCE_ZIP': str(EVIDENCE / '01_tecnico.zip')}
        for name in ['preparar_evidencias.py', 'avaliar_371.py']:
            subprocess.run([sys.executable, '-X', 'utf8', str(scripts / name)], cwd=scripts, env=env, check=True)
        generated = read(scripts / 'entrega/metricas_por_configuracao.json')['counts']
        assert generated == archived, 'Semantic rubric scores differ'
        status['table_11_semantic_rules_match'] = True
    status['table_7'] = 'Qualitative historical comparison; complete original Elasticsearch outputs not located. Not recomputed.'
    (output / 'VERIFICACAO.json').write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recalcular', action='store_true')
    parser.add_argument('--rubricas', action='store_true', help='Also execute original semantic rubric rules with the published 19/10 snapshot')
    parser.add_argument('--saida', type=Path, default=REPOSITORY / '.tmp/conferencia_artigo')
    args = parser.parse_args()
    if args.rubricas and not args.recalcular:
        parser.error('--rubricas requires --recalcular')
    if args.recalcular:
        result = recalculate(args.saida, args.rubricas)
        print(json.dumps({key: value for key, value in result.items() if key != 'table_5'}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
