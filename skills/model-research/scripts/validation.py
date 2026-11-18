"""Read-only schema, identity and CSV/table consistency checks; no model calls."""
from collections import Counter, defaultdict
import csv
import io
import json
from pathlib import Path
import sqlite3

from common import ResearchError, atomic_write, digest, now, write_json
from evidence import read_dossier
from identity import READONLY_TYPES, identity, normalize, resolve_fields, source_value
from sync import verify_sources


def baseline_snapshot(directory):
    """Never create or advance the synchronization database while validating."""
    path = Path(directory) / 'state.sqlite3'
    if not path.exists():
        return {}, {}
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        connection.execute('BEGIN')
        values = {(e, f): json.loads(v) for e, f, v in connection.execute('SELECT entity,field,value FROM baselines')}
        mappings = dict(connection.execute('SELECT entity,record_id FROM mappings'))
        return values, mappings
    finally:
        connection.close()


def execute(cfg, state, batch, backend):
    if cfg.get('allow_writes', False):
        raise ResearchError('validation requires allow_writes=false')
    issues, tables = [], {}

    def issue(reason, severity='error', **context):
        issues.append({'reason': reason, 'severity': severity, **context})

    for entry in batch.get('issues', []):
        issue(entry['reason'], **{k: v for k, v in entry.items() if k != 'reason'})
    try:
        verify_sources(batch)
    except ResearchError as exc:
        issue('source_integrity_failed', detail=str(exc))
    if batch.get('status') != 'ready':
        issue('input_incomplete')
    if batch.get('readiness') not in ('observed_stable', 'producer_confirmed') and not cfg.get('allow_unconfirmed_input'):
        issue('input_not_stable', severity='warning')
    baseline_dir = Path(cfg.get('validation', {}).get('baseline_state_dir', state.root))
    if cfg.get('validation', {}).get('baseline_state_dir') and not (baseline_dir / 'state.sqlite3').is_file():
        issue('baseline_unavailable', detail='configured synchronization database is missing')
    try:
        baselines, mappings = baseline_snapshot(baseline_dir)
    except (sqlite3.Error, ValueError) as exc:
        issue('baseline_unavailable', detail=type(exc).__name__)
        baselines, mappings = {}, {}
    by_role = defaultdict(list)
    for item in batch.get('items', []):
        by_role[item['role']].append(item)

    for role, spec in cfg['roles'].items():
        stats = {'remote_rows': 0, 'input_rows': len(by_role[role]), 'matched_rows': 0,
                 'checked_values': 0, 'equal_values': 0, 'historical_rows': 0, 'empty_rows': 0}
        tables[role] = stats
        try:
            schema, records = backend.snapshot(role, spec)
            snapshot = {'observed_at': now(), 'fields': schema, 'records': records}
            target = state.root / 'snapshots' / (role + '-' + digest(snapshot)[:24] + '.json')
            write_json(target, snapshot)
            stats.update(remote_rows=len(records), schema_fields=len(schema), snapshot=str(target))
            fields = resolve_fields(spec, schema)
        except (ResearchError, OSError, ValueError) as exc:
            issue('table_snapshot_or_schema_failed', role=role, detail=str(exc))
            continue
        index, ids = defaultdict(list), set()
        for record in records:
            rid = record.get('record_id')
            if not rid or rid in ids:
                issue('invalid_or_duplicate_record_id', role=role, record_id=rid)
                continue
            ids.add(rid)
            if all(record['fields'].get(f['id']) in (None, '', []) for f in fields.values()):
                stats['empty_rows'] += 1
                continue
            values = {}
            for key, field in fields.items():
                if field['type'] in READONLY_TYPES:
                    continue
                try:
                    values[key] = normalize(record['fields'].get(field['id']), field)
                except (ResearchError, ValueError, TypeError) as exc:
                    issue('invalid_remote_value', role=role, record_id=rid, field=key,
                          field_name=field.get('name'), detail=str(exc))
            try:
                eid, _ = identity(role, spec, values)
                index[eid].append(record)
            except (ResearchError, ValueError) as exc:
                missing = [key for key in spec['identity'] if values.get(key) in (None, '', [])]
                issue('remote_identity_incomplete', severity='warning', role=role, record_id=rid,
                      field=','.join(missing), detail=str(exc))
            for key in spec.get('required_on_create', []):
                if key in spec['identity']:
                    continue  # The same missing identity cell has already been reported.
                if values.get(key) in (None, '', []):
                    issue('required_value_missing', severity='warning', role=role, record_id=rid, field=key)
        for eid, matches in index.items():
            if len(matches) > 1:
                issue('duplicate_remote_identity', role=role, entity_id=eid,
                      record_ids=[r['record_id'] for r in matches])
        input_ids = {item['entity_id'] for item in by_role[role]}
        stats['historical_rows'] = sum(len(rows) for eid, rows in index.items() if eid not in input_ids)
        seen = set()
        for item in by_role[role]:
            eid = item['entity_id']
            context = {'role': role, 'entity_id': eid, 'source_row': item.get('source_row')}
            if eid in seen:
                issue('duplicate_input_identity', **context)
                continue
            seen.add(eid)
            if item.get('identity_conflict'):
                issue(item['identity_conflict'], **context)
            matches = index.get(eid, [])
            if not matches:
                issue('missing_remote_record', **context)
            elif len(matches) == 1:
                stats['matched_rows'] += 1
                context['record_id'] = matches[0]['record_id']
                if eid in mappings and mappings[eid] != matches[0]['record_id']:
                    issue('record_mapping_changed', expected_record_id=mappings[eid], **context)
            mirror = {}
            old = baseline_dir / 'dossiers' / (eid + '.md')
            if old.exists():
                try:
                    mirror = read_dossier(old)[0].get('controlled_fields', {})
                except (ResearchError, OSError, ValueError):
                    issue('baseline_metadata_unreadable', severity='warning', **context)
            for key, rule in spec['fields'].items():
                raw = item.get('raw_fields', {}).get(key)
                field = fields[key]
                if raw in (None, '') or field['type'] in READONLY_TYPES:
                    continue
                try:
                    expected = source_value(raw, field, rule)
                except (ResearchError, ValueError, TypeError) as exc:
                    issue('invalid_csv_value', field=key, field_name=field.get('name'), detail=str(exc), **context)
                    continue
                if len(matches) != 1 or rule.get('policy') != 'ai' or not rule.get('accept_upstream'):
                    continue
                try:
                    actual = normalize(matches[0]['fields'].get(field['id']), field)
                except (ResearchError, ValueError, TypeError):
                    continue  # Already reported during the full-table scan.
                stats['checked_values'] += 1
                if actual == expected:
                    stats['equal_values'] += 1
                    continue
                has_base = (eid, key) in baselines
                base = baselines.get((eid, key))
                saved = mirror.get(key, {})
                protected = (saved.get('origin') == 'remote_mirror' and
                             saved.get('source_value_at_mirror') == raw)
                if protected or has_base and expected == base and actual != base:
                    reason, severity = 'preserved_human_change', 'info'
                elif has_base and actual != base:
                    reason, severity = 'both_sides_changed', 'error'
                elif not has_base and actual not in (None, '', []):
                    reason, severity = 'initial_baseline_difference', 'warning'
                else:
                    reason, severity = 'csv_remote_mismatch', 'error'
                issue(reason, severity=severity, field=key, field_name=field.get('name'),
                      expected=expected, actual=actual, **context)

    counts = dict(Counter(i['severity'] for i in issues))
    report = {'schema_version': 1, 'business_date': batch['business_date'], 'checked_at': now(),
              'status': 'partial' if counts.get('error') or counts.get('warning') else 'completed',
              'batch_id': batch.get('batch_id'), 'readiness': batch.get('readiness'),
              'remote_writes': 0, 'model_calls': False, 'factual_verification': False,
              'scope': 'mapped fields in all configured tables; compare only current CSV rows; historical rows are retained',
              'tables': tables, 'counts': counts, 'issues': issues}
    return save_report(state, report)


def save_report(state, report):
    report_id = 'validation_' + digest(report)[:24]
    folder = state.root / 'validation'
    report['report_path'] = str(folder / (report_id + '.json'))
    report['issues_csv'] = str(folder / (report_id + '.csv'))
    stream = io.StringIO(newline='')
    columns = ['severity', 'reason', 'role', 'entity_id', 'record_id', 'source_row',
               'field', 'field_name', 'expected', 'actual', 'detail']
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    for entry in report['issues']:
        writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                         for k, v in entry.items()})
    atomic_write(Path(report['issues_csv']), '\ufeff' + stream.getvalue())
    write_json(Path(report['report_path']), report)
    write_json(folder / 'latest.json', report)
    return report
