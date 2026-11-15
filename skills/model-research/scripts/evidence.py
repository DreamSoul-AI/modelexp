"""JSON-compatible YAML front matter and validated, evidence-linked Agent handoffs."""
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from common import ResearchError, atomic_write, digest, now, read_json, write_json
from identity import identity
from dossiers import display_title, merge_report, validate_report, write_index


def dossier_path(state, entity):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,39}_[a-f0-9]{24}', entity):
        raise ResearchError('invalid entity ID')
    return state.root / 'dossiers' / (entity + '.md')


def read_dossier(path):
    text = Path(path).read_text(encoding='utf-8')
    if not text.startswith('---\n') or '\n---\n' not in text[4:]:
        raise ResearchError('dossier needs JSON-compatible YAML front matter')
    header, body = text[4:].split('\n---\n', 1)
    try:
        return json.loads(header), body
    except ValueError as exc:
        raise ResearchError('v1 front matter must use JSON (valid YAML), not arbitrary YAML syntax') from exc


def save_dossier(path, meta, body):
    atomic_write(path, '---\n' + json.dumps(meta, ensure_ascii=False, indent=2, allow_nan=False) + '\n---\n' + body)


def prepare_dossiers(state, batch):
    for item in batch['items']:
        path = dossier_path(state, item['entity_id'])
        if path.exists():
            meta, body = read_dossier(path)
            if meta.get('entity_id') != item['entity_id'] or meta.get('role') != item['role']:
                raise ResearchError('dossier identity mismatch')
            changed = 'display_name' not in meta
            meta.setdefault('display_name', item['raw_fields'].get('name') or item['entity_id'])
            if batch['batch_id'] not in meta['source_batches']:
                meta['source_batches'].append(batch['batch_id'])
                changed = True
            if changed:
                save_dossier(path, meta, body)
        else:
            meta = {'schema_version': 1, 'entity_id': item['entity_id'], 'role': item['role'],
                    'identity': item['identity'], 'source_batches': [batch['batch_id']], 'controlled_fields': {}}
            meta['display_name'] = item['raw_fields'].get('name') or item['entity_id']
            meta['document_layout_version'] = 2
            body = '\n# ' + display_title(meta) + '\n\n'
            body += '## 输入资料（未核验）\n\n```json\n' + json.dumps(item['raw_fields'], ensure_ascii=False, indent=2) + '\n```\n\n'
            body += '## 人工笔记\n'
            save_dossier(path, meta, body)


def validate_evidence(entry):
    if not isinstance(entry, dict):
        raise ResearchError('evidence must be an object')
    required = ('evidence_id', 'url', 'kind', 'excerpt', 'observed_at')
    if any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in required):
        raise ResearchError('evidence requires id, URL, kind, excerpt, observed_at')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', entry['evidence_id']):
        raise ResearchError('unsafe evidence ID')
    parts = urlsplit(entry['url'])
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ResearchError('evidence URL must not contain credentials')
    try:
        if not ipaddress.ip_address(parts.hostname).is_global:
            raise ResearchError('private literal IP is not an evidence URL')
    except ValueError:
        pass
    if entry['kind'] not in ('source_statement', 'third_party', 'inference'):
        raise ResearchError('unsupported evidence kind; v1 does not assert team tests')
    from datetime import datetime
    if datetime.fromisoformat(entry['observed_at'].replace('Z', '+00:00')).tzinfo is None:
        raise ResearchError('evidence observation needs a timezone')
    return {**entry, 'content_sha256': digest(entry['excerpt'])}


def import_candidates(cfg, state, batch, path):
    packet = read_json(path)
    if packet.get('schema_version') != 1 or packet.get('batch_id') != batch['batch_id']:
        raise ResearchError('candidate packet is for a different batch or schema version')
    evidence = {}
    for raw in packet.get('evidence', []):
        entry = validate_evidence(raw)
        if entry['evidence_id'] in evidence:
            raise ResearchError('duplicate evidence ID')
        evidence[entry['evidence_id']] = entry
    discovery_path = state.root / 'batches' / (batch['batch_id'] + '-discoveries.json')
    previous = read_json(discovery_path) if discovery_path.exists() else []
    work = {item['entity_id']: item for item in batch['items'] + previous}
    incoming = list(packet.get('items', []))
    for discovery in packet.get('discoveries', []):
        role = discovery['role']
        if role not in cfg['roles']:
            raise ResearchError('discovered role is not configured')
        eid, parts = identity(role, cfg['roles'][role], discovery['identity_values'])
        if eid in work:
            raise ResearchError('duplicate discovered entity')
        item = {'entity_id': eid, 'role': role, 'identity': parts, 'raw_fields': {}, 'source_id': None,
                'source_row': None, 'identity_conflict': None, 'origin': 'agent_discovery'}
        work[eid] = item
        incoming.append({'entity_id': eid, 'fields': discovery['fields']})
    seen = set()
    validated = []
    for candidate in incoming:
        eid = candidate['entity_id']
        if eid not in work or eid in seen:
            raise ResearchError('unknown or duplicate candidate entity')
        seen.add(eid)
        item = work[eid]
        allowed = cfg['roles'][item['role']]['fields']
        fields = candidate.get('fields', {})
        if not isinstance(fields, dict) or not set(fields) <= set(allowed):
            raise ResearchError('candidate contains an unmapped field')
        for key, value in fields.items():
            if not isinstance(value, dict):
                raise ResearchError('candidate field must be an object')
            if 'context' in value and not isinstance(value['context'], dict):
                raise ResearchError('candidate context must be an object')
            refs = value.get('evidence_ids', [])
            if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
                raise ResearchError('evidence_ids must be an array of strings')
            if 'value' not in value or not refs or len(set(refs)) != len(refs) or not set(refs) <= set(evidence):
                raise ResearchError('candidate field has missing evidence references')
            if any(evidence[r]['kind'] == 'inference' for r in refs) and not allowed[key].get('allow_inference', False):
                raise ResearchError('inference is not permitted for this field')
            if not set(allowed[key].get('requires_context', [])) <= set(value.get('context', {})):
                raise ResearchError('evaluation candidate is missing protocol context')
        validated.append((item, fields))
    reports = {}
    for report in packet.get('dossiers', []):
        eid = report.get('entity_id') if isinstance(report, dict) else None
        if eid not in work or eid in reports:
            raise ResearchError('unknown or duplicate dossier entity')
        validate_report(report, evidence)
        reports[eid] = report
    # Dossiers can be researched without proposing any structured field change.
    for eid in set(reports) - seen:
        validated.append((work[eid], {}))
    # Validate everything before touching dossiers. Evidence IDs are versioned by content hash.
    evidence_root = state.root / 'evidence'
    evidence_root.mkdir(exist_ok=True)
    for entry in evidence.values():
        write_json(evidence_root / (digest(entry) + '.json'), entry)
    conflicts, imported, dossier_count = [], [], 0
    for item, fields in validated:
        state.register(item['entity_id'], item['role'], item['identity'])
        prepare_dossiers(state, {**batch, 'items': [item]})
        file = dossier_path(state, item['entity_id'])
        meta, body = read_dossier(file)
        if item['entity_id'] in reports:
            meta, body, conflict = merge_report(state, item, batch, reports[item['entity_id']], evidence, meta, body)
            if conflict:
                conflicts.append({'entity_id': item['entity_id'], 'reason': conflict})
                continue
            dossier_count += 1
        for key, value in fields.items():
            meta['controlled_fields'][key] = {**value, 'evidence': [evidence[r] for r in value['evidence_ids']]}
        save_dossier(file, meta, body)
        imported.append(item['entity_id'])
    discoveries = [x for x in work.values() if x.get('origin') == 'agent_discovery']
    write_json(discovery_path, discoveries)
    write_index(state)
    return {'imported_entities': len(imported), 'imported_entity_ids': imported, 'evidence_count': len(evidence),
            'dossier_count': dossier_count, 'discoveries': len(discoveries), 'conflicts': conflicts}
