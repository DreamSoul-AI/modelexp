"""Versioned frozen empirical percentiles and guarded, resumable recalibration."""
import math
from pathlib import Path

from common import ResearchError, digest, now, read_json, write_json
from identity import identity
from score_policy import SPECIAL, ability, language_output
from lark_adapter import UncertainWrite
from sync import schema_fingerprint

ALGORITHM = '100 * (count(reference < x) + 0.5 * count(reference == x)) / N'


def percentile(value, samples):
    values = [s['value'] for s in samples]
    if not values or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
        raise ResearchError('frozen calibration requires finite percentage scores and a nonempty cohort')
    return round(100 * (sum(x < value for x in values) + 0.5 * values.count(value)) / len(values), 8)


def columns(spec, schema):
    mapped = {r['field_id']: k for k, r in spec['fields'].items()}
    return {f['name']: (f['id'], mapped[f['id']]) for f in schema if f['id'] in mapped}


def applicable(values):
    categories = values.get('用途类别') or []
    return language_output(values.get('模态')) and bool(categories) and not set(categories) & SPECIAL


def freeze(cfg, state, backend, version):
    path = Path(cfg['scores']['reference_file'])
    if path.exists():
        raise ResearchError('reference is immutable: choose a new private reference_file for a new version')
    spec = cfg['roles']['models']
    schema, records = backend.snapshot('models', spec)
    names = columns(spec, schema)
    pairs = [name for name in names if ability(name) and '标化｜' + name in names]
    reference = {'version': version, 'created_at': now(), 'algorithm': ALGORITHM,
                 'scope': 'existing classified text-output language model configurations; special/base excluded',
                 'snapshot_sha256': digest({'schema': schema, 'records': records}), 'benchmarks': {name: [] for name in pairs}}
    for record in records:
        values = {name: record['fields'].get(fid) for name, (fid, _) in names.items()}
        if not applicable(values):
            continue
        for name in pairs:
            value = values.get(name)
            if value is not None:
                percentile(value, [{'value': value}])
                reference['benchmarks'][name].append({'record_id': record['record_id'], 'value': value})
    reference['sha256'] = digest(reference)
    write_json(path, reference)
    write_json(state.root / 'scores' / ('frozen-snapshot-' + reference['sha256'][:16] + '.json'), {'fields': schema, 'records': records})
    return {'status': 'frozen', 'reference': str(path), 'version': version,
            'sample_counts': {k: len(v) for k, v in reference['benchmarks'].items()}, 'remote_writes': 0}


def load_reference(path):
    reference = read_json(path)
    if reference.get('sha256') != digest({k: v for k, v in reference.items() if k != 'sha256'}):
        raise ResearchError('frozen reference digest mismatch')
    if reference.get('algorithm') != ALGORITHM:
        raise ResearchError('unknown frozen reference algorithm')
    return reference


def plan(cfg, state, backend):
    reference = load_reference(cfg['scores']['reference_file'])
    spec = cfg['roles']['models']
    schema, records = backend.snapshot('models', spec)
    names = columns(spec, schema)
    description = ('固定参考集合；各Benchmark版本独立；标化=100×(小于原始分的样本数+0.5×同分样本数)/N。'
                   '缺失不填0，参考集合不随新增模型改变。代码50%LCBv6+40%SWE Verified+10%HumanEval+；'
                   'Agent30%BFCLv4+40%Terminal2.1+30%τ²；数学50%AIME+30%HMMT Feb+20%MATH-500。'
                   '仅对已有子项权重归一，覆盖<70%或子项<2不出能力分。'
                   '专项与基座单列；数学年份不混排；不同工具、思考预算和协议的公开报告仅供初筛。')
    operations = []
    for record in records:
        values = {name: record['fields'].get(fid) for name, (fid, _) in names.items()}
        if not applicable(values):
            continue
        changes = {}
        for name, samples in reference['benchmarks'].items():
            if values.get(name) is not None:
                changes[names['标化｜' + name][0]] = percentile(values[name], samples)
        if cfg['scores'].get('algorithm_url') and '算法存档' in names:
            changes[names['算法存档'][0]] = cfg['scores']['algorithm_url']
        if '评分版本' in names: changes[names['评分版本'][0]] = reference['version']
        if '评分说明' in names: changes[names['评分说明'][0]] = description
        if '可比性说明' in names: changes[names['可比性说明'][0]] = description + ' 参考指纹：' + reference['sha256'][:16]
        changes = {k: v for k, v in changes.items() if record['fields'].get(k) != v}
        if changes:
            operations.append({'record_id': record['record_id'], 'before': record['fields'], 'after': changes})
    document = {'kind': 'frozen_recalibration', 'created_at': now(), 'config_hash': cfg['_hash'],
                'reference_sha256': reference['sha256'], 'schema_sha256': schema_fingerprint(schema), 'operations': operations}
    document['plan_id'] = 'calibration_' + digest(document)[:24]
    path = state.root / 'scores' / (document['plan_id'] + '.json')
    write_json(path, document)
    return {'status': 'planned', 'path': str(path), 'records': len(operations),
            'values': sum(len(op['after']) for op in operations), 'version': reference['version'], 'remote_writes': 0}


def apply(cfg, state, backend, path):
    if not cfg.get('allow_writes'):
        raise ResearchError('recalibration apply requires write authorization')
    document = read_json(path)
    if document.get('plan_id') != 'calibration_' + digest({k: v for k, v in document.items() if k != 'plan_id'})[:24] or document.get('config_hash') != cfg['_hash']:
        raise ResearchError('calibration plan hash/config mismatch')
    reference = load_reference(cfg['scores']['reference_file'])
    if document['reference_sha256'] != reference['sha256']:
        raise ResearchError('calibration reference changed')
    spec = cfg['roles']['models']
    results = []
    for offset in range(0, len(document['operations']), 100):
        schema, records = backend.snapshot('models', spec)
        if schema_fingerprint(schema) != document['schema_sha256']:
            raise ResearchError('schema changed after calibration plan')
        current = {r['record_id']: r['fields'] for r in records}
        pending = {}
        for op in document['operations'][offset:offset + 100]:
            actual = current.get(op['record_id'])
            if actual is not None and all(actual.get(k) == v for k, v in op['after'].items()):
                results.append({'record_id': op['record_id'], 'status': 'already_applied'})
            elif actual == op['before']:
                pending[op['record_id']] = op['after']
            else:
                results.append({'record_id': op['record_id'], 'status': 'conflict'})
        uncertain = False
        if pending:
            write_json(state.root / 'scores' / 'calibration-pending.json', {'plan_id': document['plan_id'], 'records': pending})
            try:
                backend.update_many('models', spec, pending)
            except UncertainWrite:
                uncertain = True
            _, after = backend.snapshot('models', spec)
            for record in after:
                rid = record['record_id']
                if rid not in pending:continue
                verified = all(record['fields'].get(k) == v for k, v in pending[rid].items())
                results.append({'record_id': rid, 'status': 'verified' if verified else 'unknown' if uncertain else 'mismatch'})
                if verified:
                    raw = {k: record['fields'].get(r['field_id']) for k, r in spec['fields'].items()}
                    eid, _ = identity('models', spec, raw)
                    state.accept(eid, rid, {k: raw[k] for k, rule in spec['fields'].items() if rule['field_id'] in pending[rid] or (rule['type'] == 'number' and rule.get('policy') == 'ai' and not state.baseline(eid, k)[0])})
        result = {'status': 'completed' if all(x['status'] in ('verified', 'already_applied') for x in results) else 'partial',
                  'plan_id': document['plan_id'], 'version': reference['version'], 'results': results}
        write_json(state.root / 'scores' / 'calibration-result.json', result)
        if uncertain:break
    return result if document['operations'] else {'status': 'completed', 'results': [], 'remote_writes': 0}
