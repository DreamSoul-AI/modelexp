"""Incremental, source-bound maintenance of code/Agent/math evaluation records."""
from datetime import datetime, timedelta
import json
import subprocess
from pathlib import Path
import sys

from common import ResearchError, digest, now, read_json, run_process, write_json
from evidence import import_candidates, dossier_path, read_dossier, save_dossier
from identity import identity, normalize
from score_policy import SPECIAL, ability, language_output, validate_observation
from score_sources import collect
import score_quota
from score_calibration import load_reference, percentile
import sync



def response_key(request):
    return digest({'entities': request['entities'], 'model': request.get('runtime', {}).get('model'),
                   'evidence': [{k:v for k,v in e.items() if k != 'observed_at'} for e in request['evidence']]})


def cached_response(folder, request, exclude):
    # Reuse only actual successful CLI artifacts for the same model, records and read sources.
    for run in sorted(folder.glob('calls/*'), key=lambda p:p.stat().st_mtime, reverse=True)[:30]:
        if run == exclude or not all((run/name).is_file() for name in ('request.json','response.json','model-result.json')):
            continue
        if (run/'failure.json').exists() or read_json(run/'model-result.json').get('exit_code') != 0:
            continue
        if response_key(read_json(run/'request.json')) == response_key(request):
            return read_json(run/'response.json'), str(run)
    return None, None

def csv_model_ready(report, business_date):
    summary = report.get('result') or {}
    model = summary.get('roles', {}).get('models', {}) if 'roles' in summary else summary
    status = model.get('status') if 'roles' in summary else report.get('status')
    allowed = ('completed',) if 'roles' in summary else ('completed', 'partial')
    return (report.get('business_date') == business_date and status in allowed
            and model.get('readiness') in ('observed_stable', 'producer_confirmed'))


def execute(cfg, state, backend, business_date, mode='plan', record_ids=None):
    settings = cfg.get('scores', {})
    if mode not in ('plan', 'apply') or mode == 'apply' and not cfg.get('allow_writes'):
        raise ResearchError('score apply requires explicit write authorization')
    if not settings.get('enabled'):
        raise ResearchError('scores.enabled is required')
    if not score_quota.seconds_until_close():
        return {'status': 'partial', 'business_date': business_date, 'reason': 'daily_window_closed',
                'processed': 0, 'model_calls': 0, 'remote_writes': 0}
    if settings.get('sync_root'):
        previous = Path(settings['sync_root']) / 'last-run.json'
        sync_result = read_json(previous) if previous.exists() else {}
        receipt = Path(settings.get('sync_state_dir', str(Path(settings['sync_root']) / 'state'))) / 'daily/models-latest.json'
        if receipt.exists():
            model_sync = read_json(receipt)
            synced = (model_sync.get('business_date') == business_date and model_sync.get('status') == 'completed'
                      and model_sync.get('readiness') in ('observed_stable', 'producer_confirmed'))
        else:
            synced = csv_model_ready(sync_result, business_date)
        if not synced:
            return {'status': 'partial', 'business_date': business_date, 'reason': 'waiting_csv_sync',
                    'readiness': 'observing', 'processed': 0, 'model_calls': 0, 'remote_writes': 0}
    spec = cfg['roles']['models']
    schema, records = backend.snapshot('models', spec)
    by_name = {f['name']: f for f in schema}
    keys = {by_name_name: key for key, rule in spec['fields'].items()
            for by_name_name, field in by_name.items() if field['id'] == rule['field_id']}
    required = ['模型名称', '获取地址', '版本', '模态', '用途类别', '证据状态', '筛选状态', '逐项评测依据', '核对日期']
    if not set(required) <= set(keys):
        raise ResearchError('score configuration is missing required mapped fields')
    metrics = {name: key for name, key in keys.items() if by_name[name]['type'] == 'number' and ability(name)}
    folder = state.root / 'scores'
    folder.mkdir(exist_ok=True)
    stamp = now().replace(':', '-')
    write_json(folder / ('snapshot-' + stamp + '.json'), {'fields': schema, 'records': records})
    receipts = folder / 'receipts'
    receipts.mkdir(exist_ok=True)
    issues, eligible, excluded = [], [], 0
    for record in records:
        if record_ids and record['record_id'] not in record_ids:
            continue
        values = {name: record['fields'].get(spec['fields'][key]['field_id']) for name, key in keys.items()}
        if not language_output(values.get('模态')):
            excluded += 1
            continue
        try:
            raw = {key: record['fields'].get(rule['field_id']) for key, rule in spec['fields'].items()}
            eid, parts = identity('models', spec, raw)
        except (ResearchError, ValueError):
            issues.append({'record_id': record['record_id'], 'reason': 'incomplete_identity'})
            continue
        fingerprint = digest(record['fields'])
        receipt_path = receipts / (record['record_id'] + '.json')
        previous = read_json(receipt_path) if receipt_path.exists() else {}
        if previous.get('retry_after') and datetime.fromisoformat(previous['retry_after']) > datetime.fromisoformat(now()):
            continue
        age = datetime.fromisoformat(now()) - datetime.fromisoformat(previous.get('checked_at', '2000-01-01T00:00:00+00:00'))
        if previous.get('fingerprint') == fingerprint and age < timedelta(hours=settings.get('recheck_hours', 24)):
            continue
        item = {'entity_id': eid, 'role': 'models', 'identity': parts, 'raw_fields': {k:v for k,v in raw.items() if spec['fields'][k].get('policy') != 'ai'},
                'source_id': None, 'source_row': None, 'record_id': record['record_id']}
        eligible.append((bool(values.get('用途类别')), previous.get('checked_at', ''), record, item, values))
    eligible.sort(key=lambda x: (x[0], x[1], x[2]['record_id']))
    limit = settings.get('max_entities_per_run', 3)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
        raise ResearchError('scores.max_entities_per_run must be between 1 and 10')
    selected = eligible[:limit]
    result = {'status': 'partial' if eligible or issues else 'completed', 'business_date': business_date,
              'records_scanned': len(records), 'non_text_output_excluded': excluded,
              'eligible': len(eligible), 'processed': 0, 'issues': issues, 'remote_writes': 0,
              'model_calls': 0, 'abilities': ['code', 'agent', 'math']}
    def finish():
        write_json(folder / 'latest.json', result)
        return result
    if not selected:
        return finish()
    counter_path = folder / ('calls-' + now()[:10] + '.json')
    counter = read_json(counter_path) if counter_path.exists() else {'calls': 0}
    batch = {'schema_version': 1, 'batch_id': 'batch_' + digest([cfg['_hash'], stamp, [x[3] for x in selected]])[:24],
             'business_date': business_date, 'received_at': now(), 'config_hash': cfg['_hash'],
             'status': 'ready', 'readiness': 'score_source_evidence', 'sources': [],
             'items': [x[3] for x in selected], 'issues': []}
    state.save_batch(batch)
    evidence, failures = collect({'entities': batch['items'], 'roles': cfg['roles']})
    run = folder / 'calls' / batch['batch_id']
    run.mkdir(parents=True, exist_ok=True)
    write_json(run / 'sources.json', {'evidence': evidence, 'failures': failures})
    previous_receipts = {record['record_id']: (read_json(receipts / (record['record_id'] + '.json'))
                         if (receipts / (record['record_id'] + '.json')).exists() else {})
                         for _, _, record, _, _ in selected}
    unchanged = set()
    for _, _, record, item, _ in selected:
        own = [e for e in evidence if e['entity_id'] == item['entity_id']]
        source_hash = digest([(e['url'], e.get('source_sha256') or digest(e['excerpt'])) for e in own])
        previous = previous_receipts[record['record_id']]
        if own and previous.get('source_fingerprint') == source_hash and previous.get('fingerprint') == digest(record['fields']):
            unchanged.add(item['entity_id'])
            write_json(receipts / (record['record_id'] + '.json'), {**previous, 'checked_at': now()})
            result['processed'] += 1
    evidence = [e for e in evidence if e['entity_id'] not in unchanged]
    sourced = {e['entity_id'] for e in evidence}
    if unchanged and not sourced:
        result.update(reason='sources_unchanged', status='partial' if issues or len(eligible) > result['processed'] else 'completed')
        return finish()
    if not sourced:
        result.update(reason='sources_unavailable', source_failures=failures)
        for _, _, record, _, _ in selected:
            write_json(receipts / (record['record_id'] + '.json'), {'checked_at': now(), 'status': 'source_failed',
                'retry_after': (datetime.fromisoformat(now()) + timedelta(hours=6)).isoformat()})
        return finish()
    request = {'entities': [{**{k: item[k] for k in ('entity_id', 'record_id', 'identity')},
                            'allowed_score_fields': list(metrics),
                            'current_values': {k: v for k, v in values.items() if k in metrics or k in ('模型名称', '获取地址', '版本', '模态', '任务类型', '用途类别')}}
                           for _, _, _, item, values in selected if item['entity_id'] in sourced],
               'evidence': evidence, 'runtime': {k: settings[k] for k in ('codex_state_dir', 'codex_command', 'model') if k in settings}}
    request['runtime']['timeout_seconds'] = settings.get('model_timeout_seconds', 400)
    write_json(run / 'request.json', request)
    packet, cached_call = cached_response(folder, request, run)
    if packet is None:
        budget = settings.get('max_calls_per_day')
        if budget is not None and counter['calls'] >= budget:
            result['reason'] = 'daily_model_budget_reached'
            return finish()
        ready, quota = score_quota.available(settings)
        if not ready:
            result.update(reason=quota['reason'], quota=quota)
            return finish()
    remaining = score_quota.seconds_until_close()
    if remaining <= 5:
        result['reason'] = 'daily_window_closed'
        return finish()
    # Let the inner CLI wrapper stop its own process group before the outer deadline.
    timeout = min(settings.get('model_timeout_seconds', 400), remaining - 5)
    request['runtime']['timeout_seconds'] = timeout
    write_json(run / 'request.json', request)
    command = [sys.executable, str(Path(__file__).with_name('score_agent.py')), str(run / 'request.json')]
    try:
        if packet is None:
            counter['calls'] += 1
            write_json(counter_path, counter)
            result['model_calls'] = 1
            response = run_process(command, timeout=min(timeout + 30, remaining))
            if response.returncode:
                raise ResearchError('score agent failed; inspect private call artifacts')
            packet = json.loads(response.stdout)
        else:
            result['reused_call'] = cached_call
        entries = {row['record_id']: row for row in packet['items']}
        expected = {x[2]['record_id'] for x in selected if x[3]['entity_id'] in sourced}
        if len(entries) != len(packet['items']) or set(entries) != expected:
            raise ResearchError('score response omitted or added records')
        sources = {e['evidence_id']: e for e in evidence}
        reference = load_reference(settings['reference_file']) if settings.get('reference_file') else {'benchmarks': {}}
        candidates = []
        for _, _, record, item, values in selected:
            entry = entries.get(record['record_id'])
            if not entry:
                continue
            result['processed'] += 1
            own_sources = {ref: source for ref, source in sources.items() if source['entity_id'] == item['entity_id']}
            source = own_sources.get(entry['evidence_id'])
            quote = entry['classification_quote']
            if not source or not quote or quote not in source['excerpt']:
                raise ResearchError('classification must quote this model source')
            if not entry['is_language_model'] or entry['category'] == '不适用':
                write_json(receipts / (record['record_id'] + '.json'), {'checked_at': now(),
                    'fingerprint': digest(record['fields']), 'status': 'scope_excluded', 'call': str(run),
                    'source_fingerprint': digest([(e['url'], e.get('source_sha256') or digest(e['excerpt'])) for e in own_sources.values()])})
                continue
            fields = {}
            def propose(name, value, ref, context=None):
                if name in keys:
                    fields[keys[name]] = {'value': value, 'evidence_ids': [ref], 'context': context or {}}
            category = entry['category']
            propose('用途类别', [category], entry['evidence_id'])
            special = category in SPECIAL
            propose('筛选状态', ['基座单列' if category == '基座研究' else '专项用途单列' if special else
                             '可按单项筛选' if any(values.get(k) is not None for k in metrics) else '证据不足'], entry['evidence_id'])
            if entry['observations'] or not values.get('证据状态'):
                propose('证据状态', ['已核对公开成绩' if entry['observations'] else '已查原始来源未找到目标成绩'], entry['evidence_id'])
            propose('核对日期', now()[:10], entry['evidence_id'])
            details = ['本轮只核对代码、Agent、数学；非团队实测。', '分类依据：' + quote + '\n' + source['url']]
            published_scores = 0
            seen_fields = set()
            for observation in entry['observations']:
                if observation['field'] in seen_fields:
                    raise ResearchError('duplicate score observation field')
                seen_fields.add(observation['field'])
                value = validate_observation(observation, metrics, own_sources)
                if special:
                    continue
                field = observation['field']
                details.append(field + ' = ' + str(value) + '\n' + observation['quote'] + '\n' +
                               observation['benchmark_version'] + '；' + observation['configuration'] + '\n' +
                               own_sources[observation['evidence_id']]['url'])
                context = {k: observation[k] for k in ('benchmark_version', 'configuration')}
                normalized = '标化｜' + field
                if normalized in keys:
                    anchors = reference.get('benchmarks', {}).get(field, [])
                    scaled = percentile(value, anchors) if anchors else None
                    if scaled is None:
                        issues.append({'record_id': record['record_id'], 'field': field, 'reason': 'needs_frozen_calibration', 'candidate': value})
                        continue
                    propose(normalized, scaled, observation['evidence_id'])
                propose(field, value, observation['evidence_id'], context)
                published_scores += 1
            if published_scores and not special:
                propose('筛选状态', ['可按单项筛选'], entry['evidence_id'])
            if any(name.startswith('标化｜') and key in fields for name, key in keys.items()):
                propose('评分版本', reference.get('version', 'frozen-reference'), entry['evidence_id'])
            years = [year for year in ('2026', '2025') if any(year in o['field'] and ability(o['field']) == 'math' for o in entry['observations'])]
            if years and not special:
                propose('数学评分组', years[0], entry['evidence_id'])
            for discovery in entry['new_benchmarks']:
                if discovery['ability'] not in result['abilities'] or discovery['evidence_id'] not in own_sources or not discovery['quote'] or discovery['quote'] not in own_sources[discovery['evidence_id']]['excerpt']:
                    raise ResearchError('new Benchmark requires evidence within a fixed ability')
                issues.append({'record_id': record['record_id'], 'reason': 'benchmark_mapping_candidate', **discovery})
            text = '\n\n'.join(details)
            old = values.get('逐项评测依据') or ''
            if text not in old:
                propose('逐项评测依据', (old + '\n\n' + text).strip(), entry['evidence_id'])
            # These two fields are explicitly append-only evidence and the actual check date.
            # Preserve the current text, then let guarded apply reject concurrent changes.
            state.accept(item['entity_id'], record['record_id'],
                         {keys[k]: normalize(values.get(k), by_name[k]) for k in ('逐项评测依据', '核对日期')})
            candidates.append({'entity_id': item['entity_id'], 'fields': fields})
        accepted_ids = {candidate['entity_id'] for candidate in candidates}
        batch = {**batch, 'batch_id': 'batch_' + digest([batch['batch_id'], sorted(accepted_ids)])[:24],
                 'items': [item for item in batch['items'] if item['entity_id'] in accepted_ids]}
        state.save_batch(batch)
        result['batch_id'] = batch['batch_id']
        write_json(run / 'candidates.json', {'schema_version': 1, 'batch_id': batch['batch_id'],
                   'evidence': evidence, 'items': candidates, 'discoveries': []})
        # A new check may omit scores; it must never replay a prior call's candidates.
        for candidate in candidates:
            path = dossier_path(state, candidate['entity_id'])
            if path.exists():
                header, body = read_dossier(path)
                header['controlled_fields'] = {k:v for k,v in header.get('controlled_fields', {}).items() if k in candidate['fields']}
                save_dossier(path, header, body)
        import_candidates(cfg, state, batch, run / 'candidates.json')
        document = sync.plan(cfg, state, batch, backend)
        result['plan_path'] = str(state.root / 'plans' / (document['plan_id'] + '.json'))
        result['operations'] = len(document['operations'])
        result['issues'] = issues + document['issues']
        if mode == 'apply':
            applied = sync.apply(cfg, state, document, backend)
            result['application'] = applied
            result['remote_writes'] = sum(r.get('kind') in ('create', 'update') and r.get('status') in ('verified', 'applied') for r in applied['results'])
        _, after = backend.snapshot('models', spec)
        current = {r['record_id']: r for r in after}
        for _, _, record, item, _ in selected:
            if record['record_id'] in entries and mode == 'apply':
                write_json(receipts / (record['record_id'] + '.json'), {'checked_at': now(),
                    'fingerprint': digest(current[record['record_id']]['fields']), 'status': 'checked', 'call': str(run),
                    'source_fingerprint': digest([(e['url'], e.get('source_sha256') or digest(e['excerpt'])) for e in evidence if e['entity_id'] == item['entity_id']])})
        result['status'] = 'partial' if issues or document['issues'] or (mode == 'apply' and applied['status'] != 'completed') or len(eligible) > result['processed'] else 'completed'
    except (ResearchError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        result.update(reason='score_call_or_validation_failed', error_type=type(exc).__name__)
        write_json(run / 'failure.json', {'error': str(exc), 'type': type(exc).__name__})
        for _, _, record, _, _ in selected:
            write_json(receipts / (record['record_id'] + '.json'), {'checked_at': now(), 'status': 'failed',
                'retry_after': (datetime.fromisoformat(now()) + timedelta(minutes=30)).isoformat()})
    return finish()
