"""Run independent table deliveries with shared identity and baseline protection."""
from collections import Counter
from common import ResearchError, inside, now, read_json, write_json
from evidence import prepare_dossiers
from dossiers import write_index
from ingest import ingest
from lark_adapter import LarkAdapter
import sync
import validation


def run_batch(cfg, state, batch, backend, mode):
    prepare_dossiers(state, batch)
    write_index(state)
    if (mode == 'apply' and cfg.get('allow_writes') and batch['status'] == 'ready'
            and (batch['readiness'] in ('producer_confirmed', 'observed_stable') or cfg.get('allow_unconfirmed_input'))):
        for role in {item['role'] for item in batch['items']}:
            spec = cfg['roles'][role]
            for key, rule in spec['fields'].items():
                if not rule.get('allow_new_options'):
                    continue
                if not isinstance(backend, LarkAdapter):
                    raise ResearchError('select option maintenance requires the lark backend')
                actual = next((f for f in backend.schema(spec) if f['id'] == rule['field_id']), None)
                if actual is None:
                    raise ResearchError('schema changed for mapped field: ' + key)
                if actual.get('multiple'):
                    raise ResearchError('automatic option additions currently require a single select')
                aliases = rule.get('value_aliases', {})
                names = [aliases.get(item['raw_fields'][key].strip(), item['raw_fields'][key].strip())
                         for item in batch['items'] if item['role'] == role and item['raw_fields'].get(key, '').strip()]
                backend.append_select_options(spec, rule['field_id'], names)
    document = sync.plan(cfg, state, batch, backend)
    result = {'status': batch['status'] if batch['status'] != 'ready' else 'planned',
              'business_date': batch['business_date'], 'batch_id': batch['batch_id'],
              'plan_id': document['plan_id'], 'plan_path': str(state.root / 'plans' / (document['plan_id'] + '.json')),
              'readiness': batch['readiness'], 'operations': len(document['operations']), 'issues': document['issues']}
    if mode == 'apply':
        if any(issue.get('blocking') for issue in document['issues']):
            result['status'] = 'waiting_input'
        else:
            applied = sync.apply(cfg, state, document, backend)
            result.update(applied)
            state.save_run(result)
    return result


def execute(cfg, state, backend, business_date, mode, manifest=None):
    if mode == 'validate' and cfg.get('allow_writes'):
        raise ResearchError('validation requires allow_writes=false')
    roles, reconciliation = {}, []
    if mode == 'apply':
        for plan_id in state.pending_plans():
            try:
                old = read_json(inside(state.root, 'plans', plan_id + '.json'))
                reconciliation.append(sync.apply(cfg, state, old, backend, verify_only=True))
            except (ResearchError, OSError, ValueError) as exc:
                reconciliation.append({'plan_id': plan_id, 'status': 'unresolved', 'reason': str(exc)})
    started_at = now()
    for role, spec in cfg['roles'].items():
        try:
            batch = ingest(cfg, state, business_date, backend if isinstance(backend, LarkAdapter) else None,
                           manifest, role=role)
        except (ResearchError, OSError, ValueError) as exc:
            batch = {'business_date': business_date, 'status': 'waiting_input', 'readiness': 'invalid',
                     'items': [], 'sources': [], 'issues': [{'role': role, 'reason': 'invalid_input', 'detail': str(exc)}]}
        if mode == 'validate':
            # A broken source must not suppress the other tables' comparisons.
            roles[role] = validation.execute({**cfg, 'roles': {role: spec}}, state, batch, backend)
        elif not batch.get('batch_id'):
            roles[role] = {'status': 'partial', 'business_date': business_date, 'readiness': 'invalid',
                           'results': [], 'issues': batch['issues']}
        elif not batch['sources'] and not batch['issues']:
            roles[role] = {'status': 'skipped', 'business_date': business_date, 'readiness': 'missing_optional_input',
                           'results': [], 'issues': []}
        else:
            try:
                roles[role] = run_batch(cfg, state, batch, backend, mode)
            except (ResearchError, OSError, ValueError) as exc:
                roles[role] = {'status': 'partial', 'business_date': business_date, 'batch_id': batch['batch_id'],
                               'readiness': batch['readiness'], 'results': [],
                               'issues': [{'role': role, 'reason': 'table_sync_failed', 'detail': str(exc)}]}
        if mode == 'apply':
            # Publish immediately: model scoring need not wait for a later table in this worker.
            write_json(state.root / 'daily' / (role + '-latest.json'),
                       {**roles[role], 'finished_at': now(), 'config_hash': cfg['_hash']})
    results = [{**entry, 'role': role} for role, value in roles.items() for entry in value.get('results', [])]
    issues = [{**entry, 'role': role} for role, value in roles.items() for entry in value.get('issues', [])]
    statuses = {r['status'] for r in roles.values()}
    good = {'completed', 'skipped'} if mode != 'plan' else {'planned', 'skipped'}
    status = ('completed' if mode != 'plan' else 'planned') if statuses <= good else 'partial'
    if mode != 'validate' and 'waiting_input' in statuses and statuses <= {'waiting_input', 'skipped'}:
        status = 'waiting_input'
    ready = {r['readiness'] for r in roles.values() if r['status'] != 'skipped'}
    readiness = next(iter(ready)) if len(ready) == 1 else 'observing'
    # Preserve the single-table CLI contract while adding explicit role outcomes.
    report = dict(next(iter(roles.values()))) if len(roles) == 1 else {}
    report.update(schema_version=1, business_date=business_date, started_at=started_at, finished_at=now(),
                  status=status, readiness=readiness, roles=roles, issues=issues, results=results,
                  operations=sum(r.get('operations', 0) for r in roles.values()), reconciliation=reconciliation,
                  model_calls=False if mode == 'validate' else 0)
    if mode == 'validate':
        report.update(checked_at=now(), remote_writes=0, factual_verification=False,
                      scope='independent table checks; compare only available current CSV rows; historical rows retained',
                      tables={role: value['tables'][role] for role, value in roles.items()},
                      counts=dict(Counter(i['severity'] for i in issues)))
        return validation.save_report(state, report)
    report['counts'] = dict(Counter(r['status'] for r in results))
    write_json(state.root / 'daily' / ('latest-' + mode + '.json'), report)
    return report
