"""Field-level three-way planning, guarded application, and conservative reconciliation."""
from collections import Counter
from pathlib import Path
import hashlib
import re
import uuid

from common import ResearchError, digest, now, read_json, write_json
from evidence import dossier_path, prepare_dossiers, read_dossier, save_dossier, validate_evidence
from identity import READONLY_TYPES, identity, normalize, resolve_fields, source_value, url_identity


def verify_sources(batch):
    for source in batch['sources']:
        path = Path(source['path'])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise ResearchError('immutable batch source is missing or changed')


def schema_fingerprint(schema):
    # API list order and option display colors are not schema changes.
    rows = []
    for field in schema:
        row = {k: field[k] for k in ('id', 'name', 'type', 'multiple', 'expression', 'link_table') if k in field}
        if 'options' in field:
            row['options'] = sorted(o['name'] for o in field['options'])
        rows.append(row)
    return digest(sorted(rows, key=lambda f: f['id']))


def remote_index(role, spec, schema, records):
    fields = resolve_fields(spec, schema)
    index, unidentifiable = {}, []
    for record in records:
        if all(record['fields'].get(field['id']) in (None, '', []) for field in fields.values()):
            continue
        try:
            values = {key: normalize(record['fields'].get(f['id']), f) for key, f in fields.items()
                      if key in spec['identity']}
            eid, _ = identity(role, spec, values)
        except (ResearchError, ValueError):
            unidentifiable.append(record['record_id'])
            continue
        index.setdefault(eid, []).append(record)
    return fields, index, unidentifiable


def proposal(item, rule, key, actual, header):
    controlled = header.get('controlled_fields', {})
    mirrored = controlled.get(key, {})
    unchanged_mirror = mirrored.get('origin') == 'remote_mirror' and item['raw_fields'].get(key) == mirrored.get('source_value_at_mirror')
    if rule.get('prefer_upstream') and rule.get('accept_upstream') and not unchanged_mirror:
        if item['raw_fields'].get(key, '') == '':
            return None, False, None
        raw = item['raw_fields'][key]
        return source_value(raw, actual, rule), True, digest({'upstream': raw})
    if key in controlled:
        result = controlled[key]
        if not isinstance(result, dict) or 'value' not in result:
            raise ResearchError('malformed controlled field')
        if result.get('origin') == 'remote_mirror' and rule.get('accept_upstream') and key in item['raw_fields']:
            raw = item['raw_fields'][key]
            if raw != result.get('source_value_at_mirror') and raw != '':
                return source_value(raw, actual, rule), True, digest({'upstream': raw})
        value = normalize(result['value'], actual)
        refs = result.get('evidence_ids', [])
        evidence = result.get('evidence', [])
        if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs) or not isinstance(evidence, list):
            raise ResearchError('malformed dossier evidence references')
        for entry in evidence:
            validate_evidence(entry)
        valid = bool(refs) and len(refs) == len(set(refs)) == len(evidence) and set(refs) == {e.get('evidence_id') for e in evidence}
        valid = valid and all(e.get('content_sha256') == digest(e.get('excerpt')) for e in evidence)
        valid = valid and (rule.get('allow_inference', False) or all(e.get('kind') != 'inference' for e in evidence))
        valid = valid and set(rule.get('requires_context', [])) <= set(result.get('context', {}))
        return value, valid, digest(result)
    if rule.get('accept_upstream', False) and key in item['raw_fields']:
        raw = item['raw_fields'][key]
        if raw != '':
            return source_value(raw, actual, rule), True, digest({'upstream': raw})
    return None, False, None


def make_operation(kind, item, fields, old, record_id, schema_hash, proof):
    data = {'kind': kind, 'role': item['role'], 'entity_id': item['entity_id'], 'identity': item['identity'],
            'fields': fields, 'expected_old': old, 'record_id': record_id,
            'schema_hash': schema_hash, 'proposal_proof': proof}
    return {**data, 'operation_id': 'op_' + digest(data)[:32]}


def creation_blocker(item, spec, fields, records, unidentified):
    guards = spec.get('creation_guard_keys', [])
    if unidentified and not guards:
        return 'unidentified_remote_records_block_creation'
    canonical = lambda value: re.sub(r'[^\w]', '', str(value).casefold())
    target = dict(item['identity'])
    guard_values = {key: item.get('raw_fields', {}).get(key) or item.get('fields', {}).get(key) or target.get(key) for key in guards}
    if any(not value for value in guard_values.values()):
        return 'creation_guard_missing_identity'
    for record in records:
        for key in guards:
            value = record['fields'].get(fields[key]['id'])
            if value and canonical(value) == canonical(guard_values[key]):
                if spec.get('allow_distinct_artifact_files') and item['role'] == 'artifacts' and record['record_id'] not in unidentified:
                    other, _ = identity('artifacts', spec, {k:record['fields'].get(f['id']) for k,f in fields.items()})
                    if other != item['entity_id']:
                        continue
                return 'remote_name_or_alias_requires_adoption'
        if record['record_id'] not in unidentified:
            continue
        if any(not record['fields'].get(fields[key]['id']) for key in guards):
            return 'unidentified_remote_records_block_creation'
        for key in spec['identity']:
            if not spec['fields'][key].get('identity_url'):
                continue
            raw = record['fields'].get(fields[key]['id']) or ''
            for candidate in re.findall(r'https?://[^\s；;<>()]+', str(raw)):
                try:
                    if url_identity(candidate) == target[key]:
                        return 'ambiguous_remote_source_requires_adoption'
                except (ResearchError, ValueError):
                    continue
    return None


def coalesce_operations(operations):
    grouped = {}
    for op in operations:
        key = (op['kind'], op['role'], op['entity_id'], op['record_id'], op['schema_hash'])
        if key not in grouped:
            grouped[key] = {**op, 'fields': {}, 'expected_old': {}, 'proposal_proof': {}}
        for part in ('fields', 'expected_old', 'proposal_proof'):
            grouped[key][part].update(op[part])
    return [make_operation(op['kind'], op, op['fields'], op['expected_old'], op['record_id'],
                           op['schema_hash'], op['proposal_proof']) for op in grouped.values()]


def plan(cfg, state, batch, backend, research_issues=()):
    if batch['config_hash'] != cfg['_hash']:
        raise ResearchError('batch configuration has changed; ingest a new batch version')
    verify_sources(batch)
    extra = state.root / 'batches' / (batch['batch_id'] + '-discoveries.json')
    items = batch['items'] + (read_json(extra) if extra.exists() else [])
    prepare_dossiers(state, {**batch, 'items': items})
    operations, issues, snapshots = [], list(batch['issues']) + list(research_issues), {}
    stable = batch['readiness'] == 'observed_stable' and cfg.get('input_readiness', {}).get('strategy') == 'stable_observations'
    if batch['readiness'] != 'producer_confirmed' and not stable and not cfg.get('allow_unconfirmed_input', False):
        issues.append({'reason': 'producer_completion_unconfirmed', 'blocking': True})
    if batch['status'] != 'ready':
        issues.append({'reason': 'batch_not_ready', 'blocking': True})
    for item in items:
        role, eid = item['role'], item['entity_id']
        spec = cfg['roles'][role]
        if state.pending(eid):
            issues.append({'entity_id': eid, 'reason': 'pending_submission_requires_reconciliation'})
            continue
        alias = item.get('source_id')
        if alias:
            old = state.db.execute('SELECT entity FROM aliases WHERE role=? AND alias=?', (role, alias)).fetchone()
            if old and old[0] != eid:
                issues.append({'entity_id': eid, 'reason': 'source_id_reassigned'})
                continue
        if role not in snapshots:
            schema, records = backend.snapshot(role, spec)
            fields, index, unidentified = remote_index(role, spec, schema, records)
            snapshots[role] = fields, index, unidentified, schema_fingerprint(schema), records
        fields, index, unidentified, schema_hash, records = snapshots[role]
        matches = index.get(eid, [])
        if len(matches) > 1:
            issues.append({'entity_id': eid, 'reason': 'ambiguous_remote_identity'})
            continue
        previous = state.db.execute('SELECT record_id FROM mappings WHERE entity=?', (eid,)).fetchone()
        if previous and (not matches or matches[0]['record_id'] != previous[0]):
            issues.append({'entity_id': eid, 'reason': 'remote_mapping_changed_requires_adoption'})
            continue
        header, _ = read_dossier(dossier_path(state, eid))
        if set(header.get('controlled_fields', {})) - set(spec['fields']):
            raise ResearchError('dossier contains unmapped controlled fields')
        proposed, proofs = {}, {}
        record = matches[0] if matches else None
        for key, rule in spec['fields'].items():
            actual = fields[key]
            if actual['type'] in READONLY_TYPES or rule.get('policy', 'unassigned') in ('readonly', 'derived'):
                continue
            try:
                value, evidence_ok, proof = proposal(item, rule, key, actual, header)
                remote = normalize(record['fields'].get(actual['id']), actual) if record else None
            except (ResearchError, ValueError, TypeError) as exc:
                issues.append({'entity_id': eid, 'field': key, 'reason': 'invalid_candidate_or_remote_value', 'detail': str(exc)})
                continue
            if proof is None:
                if rule.get('policy') == 'ai' and item['raw_fields'].get(key) not in (None, ''):
                    issues.append({'entity_id': eid, 'field': key, 'reason': 'missing_research_candidate'})
                continue
            if record and key in spec['identity']:
                try:
                    candidate_id, _ = identity(role, spec, {**dict(item['identity']), key: value})
                except (ResearchError, ValueError):
                    candidate_id = None
                if candidate_id != eid:
                    issues.append({'entity_id': eid, 'field': key, 'reason': 'immutable_identity_changed'})
                    continue
            exists, baseline = state.baseline(eid, key)
            if record and remote == value:
                if not exists or baseline != value:
                    operations.append(make_operation('adopt', item, {key: value}, {key: remote}, record['record_id'], schema_hash, {key: proof}))
                continue
            if record and exists and value == baseline and remote != baseline:
                operations.append(make_operation('mirror', item, {key: remote}, {key: remote}, record['record_id'], schema_hash, {key: proof}))
                continue
            if rule.get('policy', 'unassigned') != 'ai':
                issues.append({'entity_id': eid, 'field': key, 'reason': 'protected_or_unassigned'})
                continue
            if not evidence_ok:
                issues.append({'entity_id': eid, 'field': key, 'reason': 'missing_evidence_or_protocol'})
                continue
            if (value is None or value == '' or value == []) and not rule.get('allow_clear', False):
                issues.append({'entity_id': eid, 'field': key, 'reason': 'clear_not_enabled'})
                continue
            if record:
                if not exists and not (remote in (None, '', []) and rule.get('bootstrap_empty', False)):
                    issues.append({'entity_id': eid, 'field': key, 'reason': 'needs_initial_baseline'})
                elif exists and remote != baseline:
                    issues.append({'entity_id': eid, 'field': key, 'reason': 'both_sides_changed'})
                else:
                    operations.append(make_operation('update', item, {key: value}, {key: remote}, record['record_id'], schema_hash, {key: proof}))
            else:
                proposed[key], proofs[key] = value, proof
        if not record and proposed:
            required = set(spec['identity']) | set(spec.get('required_on_create', []))
            if not spec.get('allow_create', False):
                issues.append({'entity_id': eid, 'reason': 'creation_not_enabled'})
            elif (blocker := creation_blocker({**item, 'fields': proposed}, spec, fields, records, unidentified)):
                issues.append({'entity_id': eid, 'reason': blocker})
            elif not required <= set(proposed) or any(proposed[k] is None for k in required):
                issues.append({'entity_id': eid, 'reason': 'creation_missing_required_fields'})
            else:
                new_eid, _ = identity(role, spec, proposed)
                if new_eid != eid:
                    issues.append({'entity_id': eid, 'reason': 'proposed_identity_changed'})
                else:
                    operations.append(make_operation('create', item, proposed, {}, None, schema_hash, proofs))
    operations = coalesce_operations(operations)
    body = {'schema_version': 1, 'batch_id': batch['batch_id'], 'config_hash': cfg['_hash'],
            'operations': operations, 'issues': issues}
    plan_id = 'plan_' + digest(body)[:32]
    result = {**body, 'plan_id': plan_id, 'created_at': now()}
    path = state.root / 'plans' / (plan_id + '.json')
    if path.exists():
        return read_json(path)
    write_json(path, result)
    return result


def check_plan(cfg, state, document):
    body = {k: v for k, v in document.items() if k not in ('plan_id', 'created_at')}
    if document.get('schema_version') != 1 or document.get('plan_id') != 'plan_' + digest(body)[:32]:
        raise ResearchError('plan contents or plan identity have been modified')
    if document['config_hash'] != cfg['_hash']:
        raise ResearchError('configuration differs from the saved plan')
    batch = state.batch(document['batch_id'])
    verify_sources(batch)
    for op in document['operations']:
        raw = {k: v for k, v in op.items() if k != 'operation_id'}
        if op['operation_id'] != 'op_' + digest(raw)[:32]:
            raise ResearchError('operation identity mismatch')
        if op['kind'] not in ('adopt', 'mirror', 'update', 'create'):
            raise ResearchError('unsupported operation kind')
        spec = cfg['roles'][op['role']]
        if not set(op['fields']) <= set(spec['fields']):
            raise ResearchError('operation field is not configured')
        if op['kind'] in ('create', 'update'):
            if any(spec['fields'][key].get('policy', 'unassigned') != 'ai' for key in op['fields']):
                raise ResearchError('plan exceeds the configured field whitelist')
            if op['kind'] == 'create' and not spec.get('allow_create', False):
                raise ResearchError('creation is not enabled')
    return batch


def submit_batches(cfg, state, document, backend, queued, report, items):
    """Recheck each bounded table batch, submit once, and verify by identity and values."""
    groups = {}
    for op, result in queued:
        groups.setdefault((op['role'], op['kind']), []).append((op, result))
    size = cfg.get('backend', {}).get('batch_size', 1)
    for (role, kind), entries in groups.items():
        spec = cfg['roles'][role]
        for start in range(0, len(entries), size):
            accepted = []
            try:
                schema, records = backend.snapshot(role, spec)
                fields, index, unidentified = remote_index(role, spec, schema, records)
                reserved = list(records)
                for op, result in entries[start:start + size]:
                    try:
                        if schema_fingerprint(schema) != op['schema_hash']:
                            raise ResearchError('schema changed before batch submission')
                        matches = index.get(op['entity_id'], [])
                        if kind == 'create':
                            if matches or creation_blocker(op, spec, fields, reserved, unidentified):
                                raise ResearchError('remote identity guard changed before batch submission')
                            reserved.append({'record_id': 'reserved_' + op['entity_id'],
                                             'fields': {fields[k]['id']: v for k, v in op['fields'].items()}})
                        elif len(matches) != 1 or matches[0]['record_id'] != op['record_id'] or any(
                                normalize(matches[0]['fields'].get(fields[k]['id']), fields[k]) != v for k, v in op['expected_old'].items()):
                            raise ResearchError('remote values changed before batch submission')
                        header, _ = read_dossier(dossier_path(state, op['entity_id']))
                        for key, proof in op['proposal_proof'].items():
                            value, valid, actual_proof = proposal(items[op['entity_id']], spec['fields'][key], key, fields[key], header)
                            if not valid or actual_proof != proof or value != op['fields'][key]:
                                raise ResearchError('local proposal changed before batch submission')
                        accepted.append((op, result))
                    except (ResearchError, ValueError, KeyError) as exc:
                        result.update(status='conflict', reason=str(exc))
                if not accepted:
                    continue
                verify_sources(state.batch(document['batch_id']))
                for op, _ in accepted:
                    state.mark(op['operation_id'], document['plan_id'], 'submitting', op['record_id'])
                values = [{fields[k]['id']: v for k, v in op['fields'].items()} for op, _ in accepted]
                if kind == 'create':
                    submitted_ids = set(backend.create_many(role, spec, values))
                else:
                    backend.update_many(role, spec, {op['record_id']: value for (op, _), value in zip(accepted, values)})
                    submitted_ids = {op['record_id'] for op, _ in accepted}
                after_schema, after = backend.snapshot(role, spec)
                if schema_fingerprint(after_schema) != schema_fingerprint(schema):
                    raise ResearchError('schema changed during batch write')
                _, after_index, _ = remote_index(role, spec, after_schema, after)
                for op, result in accepted:
                    rows = after_index.get(op['entity_id'], [])
                    if len(rows) == 1 and rows[0]['record_id'] in submitted_ids and all(
                            normalize(rows[0]['fields'].get(fields[k]['id']), fields[k]) == v for k, v in op['fields'].items()):
                        record_id = rows[0]['record_id']
                        state.accept(op['entity_id'], record_id, op['fields'])
                        state.mark(op['operation_id'], document['plan_id'], 'verified', record_id)
                        result['status'] = 'verified'
                    else:
                        state.mark(op['operation_id'], document['plan_id'], 'unknown', op['record_id'])
                        result['status'] = 'unknown'
            except Exception as exc:
                # All requests whose submission began remain query-only until reconciled.
                for op, result in accepted:
                    if result['status'] == 'verified':
                        continue
                    prior = state.operation(op['operation_id'])
                    if prior and prior['status'] == 'submitting':
                        state.mark(op['operation_id'], document['plan_id'], 'unknown', op['record_id'])
                        result['status'] = 'unknown'
                    else:
                        result.update(status='conflict', reason=type(exc).__name__)
                for _, result in entries[start:start + size]:
                    if result['status'] == 'queued':
                        result.update(status='conflict', reason=type(exc).__name__)
            state.save_run(report)


def apply(cfg, state, document, backend, verify_only=False):
    batch = check_plan(cfg, state, document)
    if any(x.get('blocking') for x in document['issues']):
        raise ResearchError('batch readiness blocks application; inspect the plan issues')
    if not verify_only and any(op['kind'] in ('create', 'update') for op in document['operations']) and not cfg.get('allow_writes', False):
        raise ResearchError('allow_writes is false; this plan has not been applied')
    extra = state.root / 'batches' / (batch['batch_id'] + '-discoveries.json')
    items = {x['entity_id']: x for x in batch['items'] + (read_json(extra) if extra.exists() else [])}
    report = {'schema_version': 1, 'run_id': 'run_' + uuid.uuid4().hex, 'plan_id': document['plan_id'],
              'batch_id': batch['batch_id'], 'business_date': batch['business_date'],
              'readiness': batch['readiness'],
              'started_at': now(), 'status': 'running', 'results': [], 'issues': document['issues']}
    state.save_run(report)
    batching = not verify_only and cfg.get('backend', {}).get('batch_size', 1) > 1
    snapshots, queued = {}, []
    for op in document['operations']:
        eid, role, op_id = op['entity_id'], op['role'], op['operation_id']
        spec = cfg['roles'][role]
        prior = state.operation(op_id)
        result = {'operation_id': op_id, 'entity_id': eid, 'kind': op['kind']}
        try:
            if any(p['id'] != op_id for p in state.pending(eid)):
                raise ResearchError('another pending submission for this entity requires reconciliation')
            if prior is None:
                state.mark(op_id, document['plan_id'], 'planned', op['record_id'], entity=eid)
            if not batching or role not in snapshots:
                snapshots[role] = backend.snapshot(role, spec)
            schema, records = snapshots[role]
            fields, index, unidentified = remote_index(role, spec, schema, records)
            if schema_fingerprint(schema) != op['schema_hash'] and not verify_only:
                raise ResearchError('schema changed after planning')
            matches = index.get(eid, [])
            if len(matches) > 1:
                raise ResearchError('remote identity is now ambiguous')
            record = matches[0] if matches else None
            if op['record_id'] and (not record or record['record_id'] != op['record_id']):
                raise ResearchError('target mapping or identity changed')
            current = {k: normalize(record['fields'].get(fields[k]['id']), fields[k]) if record else None for k in op['fields']}
            uncertain = prior and prior['status'] in ('submitting', 'submitted', 'unknown')
            if prior and prior['status'] == 'verified':
                if not record or current != op['fields']:
                    raise ResearchError('verified operation target was subsequently changed')
                result['status'] = 'reused'
            elif uncertain:
                if record and current == op['fields']:
                    # The observed identity and values suffice to avoid a duplicate, not to assert who wrote them.
                    state.accept(eid, record['record_id'], current)
                    state.mark(op_id, document['plan_id'], 'verified', record['record_id'], {'recovered_by': 'identity_and_values'})
                    result['status'] = 'reconciled'
                else:
                    state.mark(op_id, document['plan_id'], 'unknown', record['record_id'] if record else None,
                               {'reason': 'submission_outcome_not_confirmed'})
                    result['status'] = 'unknown'
            elif verify_only:
                result['status'] = 'not_submitted'
            else:
                header, _ = read_dossier(dossier_path(state, eid))
                item = items[eid]
                for key, proof in op['proposal_proof'].items():
                    actual_value, _, actual_proof = proposal(item, spec['fields'][key], key, fields[key], header)
                    if actual_proof != proof:
                        raise ResearchError('local proposal changed after planning')
                    if op['kind'] in ('create', 'update') and actual_value != op['fields'][key]:
                        raise ResearchError('planned value differs from its evidence-backed proposal')
                if op['kind'] == 'create' and record:
                    raise ResearchError('a matching record appeared after planning; regenerate the plan')
                if op['kind'] == 'create' and creation_blocker(op, spec, fields, records, unidentified):
                    raise ResearchError('remote identity guard changed after planning')
                if op['kind'] != 'create' and current != op['expected_old']:
                    raise ResearchError('remote values changed after planning')
                if op['kind'] in ('mirror', 'adopt'):
                    if op['kind'] == 'mirror':
                        meta, body = read_dossier(dossier_path(state, eid))
                        for key, value in op['fields'].items():
                            meta['controlled_fields'][key] = {'value': value, 'evidence_ids': [], 'evidence': [], 'origin': 'remote_mirror', 'source_value_at_mirror': item['raw_fields'].get(key)}
                        save_dossier(dossier_path(state, eid), meta, body)
                    state.accept(eid, record['record_id'], op['fields'])
                    state.mark(op_id, document['plan_id'], 'verified', record['record_id'])
                    result['status'] = 'verified_local'
                else:
                    values = {fields[key]['id']: normalize(v, fields[key]) for key, v in op['fields'].items()}
                    if any(fields[k]['type'] in READONLY_TYPES for k in op['fields']):
                        raise ResearchError('attempt to write a system/derived field')
                    if batching:
                        result['status'] = 'queued'
                        queued.append((op, result))
                        report['results'].append(result)
                        continue
                    state.mark(op_id, document['plan_id'], 'submitting', op['record_id'])
                    try:
                        record_id = backend.create(role, spec, values) if op['kind'] == 'create' else op['record_id']
                        if op['kind'] == 'update':
                            backend.update(role, spec, record_id, values)
                        state.mark(op_id, document['plan_id'], 'submitted', record_id)
                        after_schema, after = backend.snapshot(role, spec)
                        if schema_fingerprint(after_schema) != op['schema_hash']:
                            raise ResearchError('schema changed during write')
                        rows = [r for r in after if r['record_id'] == record_id]
                        if len(rows) != 1 or any(normalize(rows[0]['fields'].get(fields[k]['id']), fields[k]) != v for k, v in op['fields'].items()):
                            raise ResearchError('write has not been verified by readback')
                        state.accept(eid, record_id, op['fields'])
                        state.mark(op_id, document['plan_id'], 'verified', record_id)
                        result['status'] = 'verified'
                    except Exception:
                        # Includes post-submit file/DB failures. Do not resend without reconciliation.
                        state.mark(op_id, document['plan_id'], 'unknown', detail={'reason': 'write_or_receipt_not_verified'})
                        result['status'] = 'unknown'
        except (ResearchError, ValueError, KeyError) as exc:
            result.update(status='conflict', reason=str(exc))
        report['results'].append(result)
        state.save_run(report)
    if queued:
        submit_batches(cfg, state, document, backend, queued, report, items)
    report['finished_at'] = now()
    counts = dict(Counter(x['status'] for x in report['results']))
    report['counts'] = counts
    report['status'] = 'partial' if document['issues'] or any(k in counts for k in ('unknown', 'conflict', 'not_submitted')) else 'completed'
    state.save_run(report)
    text = '# 模型调研运行报告\n\n' + '\n'.join([f"- 运行：{report['run_id']}", f"- 状态：{report['status']}",
                                                  f"- 操作结果：{counts}", f"- 待处理项：{len(document['issues'])}"])
    from common import atomic_write
    atomic_write(state.root / 'runs' / (report['run_id'] + '.md'), text + '\n')
    return report
