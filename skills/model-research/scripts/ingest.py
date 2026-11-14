"""Receive explicit-date CSV batches and preserve each immutable content version."""
import csv
from datetime import date
import fnmatch
import hashlib
import io
from pathlib import Path
import re
import tempfile

from common import ResearchError, atomic_write, digest, now, read_json
from identity import identity


def columns_for(rule, headers):
    names = [rule.get('column', ''), *rule.get('column_aliases', [])]
    hits = [name for name in names if name in headers]
    if len(hits) != 1:
        raise ResearchError('missing or ambiguous mapped CSV column: ' + str(names))
    return hits[0]


def latest_snapshot(candidates, business_date):
    """Snapshots are independent of daily delivery; select by explicit filename date."""
    dated = []
    for entry in candidates:
        hit = re.search(r'(\d{4}-\d{2}-\d{2})(?=\.csv$)', entry['name'])
        if hit:
            try:
                stamp = date.fromisoformat(hit[1]).isoformat()
            except ValueError:
                continue
            if stamp <= business_date:
                dated.append((stamp, entry))
    newest = max((stamp for stamp, _ in dated), default=None)
    return [entry for stamp, entry in dated if stamp == newest]


def ingest(cfg, state, business_date, drive=None, manifest_path=None):
    date.fromisoformat(business_date)
    manifest = read_json(manifest_path) if manifest_path else None
    if manifest and (manifest.get('business_date') != business_date or manifest.get('complete') is not True):
        raise ResearchError('producer manifest must confirm the selected business date and completion')
    items, sources, issues = [], [], []
    for role, spec in cfg['roles'].items():
        source = spec.get('input')
        if not source:
            continue
        pattern = source['filename'].replace('{date}', business_date)
        if any(word in pattern.lower() for word in ('source_links', 'backfill')):
            raise ResearchError('source_links/backfill inputs are disabled')
        if source.get('kind', 'local') == 'local':
            folder = Path(source['directory'])
            candidates = [{'name': p.name, 'path': p} for p in folder.iterdir() if p.is_file() and fnmatch.fnmatch(p.name, pattern)] if folder.is_dir() else []
        elif source.get('kind') == 'drive' and drive:
            candidates = [f for f in drive.list_files(source['folder_token']) if f['type'] == 'file' and fnmatch.fnmatch(f['name'], pattern)]
        else:
            raise ResearchError('Drive inputs require an explicitly configured lark backend')
        if source.get('latest_snapshot', False):
            candidates = latest_snapshot(candidates, business_date)
        if len(candidates) != 1:
            if not candidates and not source.get('required', True):
                continue
            issues.append({'role': role, 'reason': 'missing_input' if not candidates else 'ambiguous_input'})
            continue
        entry = candidates[0]
        if any(word in entry['name'].lower() for word in ('source_links', 'backfill')):
            raise ResearchError('excluded input')
        if 'path' in entry:
            content = entry['path'].read_bytes()
        else:
            temp_root = state.root / 'downloads'
            temp_root.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(dir=temp_root) as folder:
                destination = Path(folder) / 'source.csv'
                drive.download(entry['token'], destination)
                content = destination.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        if manifest:
            expected = manifest.get('files', {}).get(role, {})
            if expected.get('name') != entry['name'] or expected.get('sha256') != sha:
                raise ResearchError('producer manifest file identity/hash mismatch')
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ResearchError('CSV must be UTF-8') from exc
        reader = csv.DictReader(io.StringIO(text, newline=''))
        headers = reader.fieldnames or []
        if len(set(headers)) != len(headers):
            raise ResearchError('duplicate CSV column')
        columns = {key: columns_for(rule, headers) for key, rule in spec['fields'].items() if rule.get('column')}
        identity_keys = set(spec['identity'])
        if not identity_keys <= set(columns):
            raise ResearchError('identity columns are not mapped to CSV')
        rows = list(reader)
        if not rows and not (manifest and manifest.get('files', {}).get(role, {}).get('allow_empty') is True):
            issues.append({'role': role, 'reason': 'empty_input_without_producer_confirmation'})
        seen = set()
        for number, row in enumerate(rows, 2):
            if None in row or any(v is None for v in row.values()):
                raise ResearchError(f'{role}: malformed CSV row {number}')
            # Identity columns are text in v1; other CSV values stay raw until real schema validation.
            values = {key: row[column] for key, column in columns.items()}
            try:
                entity_id, parts = identity(role, spec, values)
            except (ResearchError, ValueError) as exc:
                issues.append({'role': role, 'row': number, 'reason': 'unresolved_identity', 'detail': str(exc)})
                continue
            if entity_id in seen:
                raise ResearchError(f'{role}: duplicate entity identity in the same input')
            seen.add(entity_id)
            alias = row.get(spec.get('source_id_column')) if spec.get('source_id_column') else None
            conflict = state.register(entity_id, role, parts, alias)
            items.append({'entity_id': entity_id, 'role': role, 'identity': parts, 'raw_fields': values,
                          'source_row': number, 'source_id': alias, 'identity_conflict': conflict})
        raw = state.root / 'incoming' / (sha + '.csv')
        if raw.exists() and raw.read_bytes() != content:
            raise ResearchError('immutable source hash collision')
        if not raw.exists():
            raw.parent.mkdir(exist_ok=True)
            raw.write_bytes(content)
            raw.chmod(0o600)
        sources.append({'role': role, 'name': entry['name'], 'token': entry.get('token'), 'sha256': sha,
                        'path': str(raw), 'rows': len(rows), 'columns': headers})
    ready = bool(sources) and not any(i['reason'] in ('missing_input', 'ambiguous_input', 'empty_input_without_producer_confirmation') for i in issues)
    observed_at = now()
    readiness = 'producer_confirmed' if manifest else 'unconfirmed'
    source_keys = [{k: s[k] for k in ('role', 'sha256')} for s in sources]
    rule = cfg.get('input_readiness', {})
    if not manifest and rule.get('strategy') == 'stable_observations':
        signature = digest({'sources': source_keys, 'ready': ready})
        stable = state.observe_inputs(business_date, signature, observed_at, rule['min_interval_seconds'])
        readiness = 'observed_stable' if stable and ready else 'observing'
    fingerprint = {'date': business_date, 'sources': source_keys, 'config': cfg['_hash'],
                   'readiness': readiness, 'issues': issues}
    batch_id = 'batch_' + digest(fingerprint)[:24]
    batch = {'schema_version': 1, 'batch_id': batch_id, 'business_date': business_date, 'received_at': now(),
             'config_hash': cfg['_hash'], 'status': 'ready' if ready else 'waiting_input',
             'readiness': readiness,
             'sources': sources, 'items': items, 'issues': issues}
    state.save_batch(batch)
    return state.batch(batch_id)
