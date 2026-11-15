#!/usr/bin/env python3
"""Model research CLI. Defaults are read-only; credentials remain with lark-cli."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import json
from pathlib import Path
import sys

from common import ResearchError, digest, inside, load_config, now, read_json, write_json
from state import State
from lark_adapter import LarkAdapter, adapter_for
from ingest import ingest
from evidence import dossier_path, import_candidates, prepare_dossiers, read_dossier, save_dossier
from identity import identity, normalize
import sync
from dossiers import write_index


def demo(directory, business_date):
    root = Path(directory).resolve()
    if root.exists() and any(root.iterdir()):
        raise ResearchError('demo directory must be empty')
    root.mkdir(parents=True, exist_ok=True)
    fields = [
        {'id': 'fld_url', 'name': '入口链接', 'type': 'text'},
        {'id': 'fld_publisher', 'name': '发布主体', 'type': 'text'},
        {'id': 'fld_name', 'name': '渠道名称', 'type': 'text'},
        {'id': 'fld_note', 'name': '备注', 'type': 'text'},
    ]
    mappings = {name: {'field_id': f['id'], 'column': f['name'], 'type': f['type'],
                       'policy': 'ai', 'accept_upstream': True} for name, f in zip(('url', 'publisher', 'name', 'note'), fields)}
    mappings['url']['identity_url'] = True
    cfg = {'schema_version': 1, 'state_dir': './state', 'allow_writes': True, 'allow_unconfirmed_input': True,
           'backend': {'kind': 'file', 'path': './remote.json'},
           'roles': {'channels': {'table_id': 'demo_channels', 'identity': ['url', 'publisher'],
                                 'source_id_column': '渠道ID', 'allow_create': True,
                                 'input': {'kind': 'local', 'directory': './incoming', 'filename': 'channels_{date}.csv'},
                                 'fields': mappings}}}
    write_json(root / 'project.json', cfg)
    write_json(root / 'remote.json', {'tables': {'channels': {'fields': fields, 'records': []}}})
    folder = root / 'incoming'
    folder.mkdir()
    with (folder / f'channels_{business_date}.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['渠道ID', '入口链接', '发布主体', '渠道名称', '备注'])
        writer.writeheader()
        writer.writerows([
            {'渠道ID': 'CH-1', '入口链接': 'https://example.org/a', '发布主体': 'Example A', '渠道名称': '演示渠道 A', '备注': '演示数据；保留完整文本'},
            {'渠道ID': 'CH-2', '入口链接': 'https://example.org/b', '发布主体': 'Example B', '渠道名称': '演示渠道 B', '备注': '本地后端，不访问飞书'},
        ])
    return {'status': 'demo_created', 'config': str(root / 'project.json'), 'business_date': business_date}


def adopt(cfg, state, backend, batch_id, entity_id, record_id):
    batch = state.batch(batch_id)
    items = {x['entity_id']: x for x in batch['items']}
    if entity_id not in items:
        raise ResearchError('adopt requires an entity in the selected batch')
    item = items[entity_id]
    spec = cfg['roles'][item['role']]
    schema, records = backend.snapshot(item['role'], spec)
    fields, index, _ = sync.remote_index(item['role'], spec, schema, records)
    matches = index.get(entity_id, [])
    if len(matches) != 1 or matches[0]['record_id'] != record_id:
        raise ResearchError('adopt requires a unique matching remote identity and record ID')
    prepare_dossiers(state, {**batch, 'items': [item]})
    path = dossier_path(state, entity_id)
    meta, body = read_dossier(path)
    values = {}
    for key, field in fields.items():
        if field['type'] in ('formula', 'lookup', 'created_at', 'updated_at', 'created_by', 'updated_by', 'auto_number'):
            continue
        values[key] = normalize(matches[0]['fields'].get(field['id']), field)
        meta['controlled_fields'][key] = {'value': values[key], 'evidence_ids': [], 'evidence': [],
                                          'origin': 'remote_mirror', 'source_value_at_mirror': item['raw_fields'].get(key)}
    save_dossier(path, meta, body)
    state.accept(entity_id, record_id, values)
    return {'status': 'adopted_remote_baseline', 'entity_id': entity_id, 'record_id': record_id, 'remote_writes': 0}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    subs = result.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'inspect', 'ingest', 'plan', 'apply', 'verify', 'resume', 'run', 'validate', 'finalize-md', 'export-md', 'import-candidates', 'adopt', 'resolve-identity'):
        sub = subs.add_parser(name)
        sub.add_argument('--config', required=True)
        if name == 'export-md':
            sub.add_argument('--output', required=True)
        if name in ('ingest', 'run', 'validate'):
            sub.add_argument('--date', required=True)
            sub.add_argument('--manifest')
        if name in ('plan', 'import-candidates', 'adopt'):
            sub.add_argument('--batch', required=True)
        if name in ('run', 'plan', 'import-candidates'):
            sub.add_argument('--candidates', required=name == 'import-candidates')
        if name == 'run':
            sub.add_argument('--mode', choices=('plan', 'apply'), default='plan')
        if name in ('apply', 'verify'):
            sub.add_argument('--plan', required=True)
        if name == 'resume':
            sub.add_argument('--run', required=True)
        if name in ('adopt', 'resolve-identity'):
            sub.add_argument('--entity', required=True)
        if name == 'adopt':
            sub.add_argument('--record-id', required=True)
        if name in ('inspect', 'resolve-identity'):
            sub.add_argument('--role', required=True)
        if name == 'resolve-identity':
            sub.add_argument('--source-id', required=True)
    sub = subs.add_parser('demo')
    sub.add_argument('--directory', required=True)
    sub.add_argument('--date', default=now()[:10])
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == 'demo':
        date.fromisoformat(args.date)
        return demo(args.directory, args.date)
    cfg = load_config(args.config)
    state = State(cfg['_state'])
    backend = adapter_for(cfg)
    try:
        with state.lock():
            if args.command in ('finalize-md', 'export-md'):
                import markdown_delivery
                return markdown_delivery.finalize(state) if args.command == 'finalize-md' else markdown_delivery.export(state, args.output)
            if args.command == 'doctor':
                result = backend.doctor()
                result.update(state_dir=str(state.root), allow_writes=cfg.get('allow_writes', False))
                return result
            if args.command == 'inspect':
                spec = cfg['roles'][args.role]
                schema, records = backend.snapshot(args.role, spec)
                path = state.root / 'snapshots' / (args.role + '-' + digest({'schema': schema, 'records': records})[:24] + '.json')
                write_json(path, {'fields': schema, 'records': records, 'observed_at': now()})
                return {'status': 'read_only_snapshot', 'role': args.role, 'rows': len(records), 'schema_fields': len(schema), 'path': str(path)}
            if args.command == 'resolve-identity':
                row = state.db.execute('SELECT role FROM entities WHERE id=?', (args.entity,)).fetchone()
                if not row or row[0] != args.role:
                    raise ResearchError('unknown entity/role')
                before = state.db.execute('SELECT entity FROM aliases WHERE role=? AND alias=?', (args.role, args.source_id)).fetchone()
                write_json(state.root / 'identity-resolutions' / (digest([now(), args.role, args.source_id, args.entity]) + '.json'),
                           {'resolved_at': now(), 'role': args.role, 'source_id': args.source_id, 'old_entity': before[0] if before else None, 'entity_id': args.entity})
                with state.db:
                    state.db.execute('INSERT OR REPLACE INTO aliases VALUES (?,?,?)', (args.role, args.source_id, args.entity))
                return {'status': 'source_alias_resolved', 'remote_writes': 0}
            if args.command in ('apply', 'verify', 'resume'):
                if args.command == 'resume':
                    old = state.run(args.run)
                    path = inside(state.root, 'plans', old['plan_id'] + '.json')
                else:
                    path = Path(args.plan).resolve()
                document = read_json(path)
                return sync.apply(cfg, state, document, backend, verify_only=args.command == 'verify')
            if args.command in ('ingest', 'run', 'validate'):
                if args.command == 'validate' and cfg.get('allow_writes', False):
                    raise ResearchError('validation requires allow_writes=false')
                try:
                    batch = ingest(cfg, state, args.date, backend if isinstance(backend, LarkAdapter) else None, args.manifest)
                except ResearchError as exc:
                    if args.command != 'validate':
                        raise
                    batch = {'business_date': args.date, 'status': 'waiting_input', 'readiness': 'invalid',
                             'items': [], 'sources': [],
                             'issues': [{'reason': 'invalid_input', 'detail': str(exc)}]}
                if args.command == 'validate':
                    import validation
                    return validation.execute(cfg, state, batch, backend)
                prepare_dossiers(state, batch)
                write_index(state)
                if args.command == 'ingest':
                    return {'status': batch['status'], 'batch_id': batch['batch_id'], 'readiness': batch['readiness'],
                            'entities': len(batch['items']), 'issues': batch['issues']}
            else:
                batch = state.batch(args.batch)
            if args.command == 'adopt':
                return adopt(cfg, state, backend, args.batch, args.entity, args.record_id)
            if getattr(args, 'candidates', None):
                candidate_result = import_candidates(cfg, state, batch, args.candidates)
                if args.command == 'import-candidates':
                    return candidate_result
            reconciliation = []
            if args.command == 'run' and args.mode == 'apply':
                for plan_id in state.pending_plans():
                    try:
                        old = read_json(inside(state.root, 'plans', plan_id + '.json'))
                        reconciliation.append(sync.apply(cfg, state, old, backend, verify_only=True))
                    except ResearchError as exc:
                        reconciliation.append({'plan_id': plan_id, 'status': 'unresolved', 'reason': str(exc)})
            if args.command == 'run' and args.mode == 'apply' and cfg.get('allow_writes') and batch['status'] == 'ready' and (
                    batch['readiness'] in ('producer_confirmed', 'observed_stable') or cfg.get('allow_unconfirmed_input')):
                for role, spec in cfg['roles'].items():
                    for key, rule in spec['fields'].items():
                        if rule.get('allow_new_options'):
                            if not isinstance(backend, LarkAdapter):
                                raise ResearchError('select option maintenance requires the lark backend')
                            # Current workflow permits append-only publisher labels, never type conversion.
                            actual = next(f for f in backend.schema(spec) if f['id'] == rule['field_id'])
                            if actual.get('multiple'):
                                raise ResearchError('automatic option additions currently require a single select')
                            aliases = rule.get('value_aliases', {})
                            names = [aliases.get(item['raw_fields'][key].strip(), item['raw_fields'][key].strip())
                                     for item in batch['items'] if item['role'] == role and item['raw_fields'].get(key, '').strip()]
                            backend.append_select_options(spec, rule['field_id'], names)
            document = sync.plan(cfg, state, batch, backend)
            path = state.root / 'plans' / (document['plan_id'] + '.json')
            if args.command == 'run' and args.mode == 'apply':
                if any(issue.get('blocking') for issue in document['issues']):
                    return {'status': 'waiting_input', 'batch_id': batch['batch_id'], 'plan_id': document['plan_id'],
                            'readiness': batch['readiness'],
                            'plan_path': str(path), 'operations': len(document['operations']),
                            'issues': document['issues'], 'reconciliation': reconciliation}
                report = sync.apply(cfg, state, document, backend)
                report.update(reconciliation=reconciliation, plan_path=str(path))
                state.save_run(report)
                return report
            return {'status': batch['status'] if batch['status'] != 'ready' else 'planned',
                    'batch_id': batch['batch_id'], 'plan_id': document['plan_id'], 'plan_path': str(path),
                    'readiness': batch['readiness'],
                    'operations': len(document['operations']), 'issues': document['issues']}
    finally:
        state.close()


if __name__ == '__main__':
    try:
        result = main()
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        status = result.get('status')
        sys.exit(3 if status in ('partial', 'waiting_input') else 0)
    except (ResearchError, ValueError, KeyError, OSError) as exc:
        print(json.dumps({'ok': False, 'error': {'type': type(exc).__name__, 'message': str(exc)}}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
