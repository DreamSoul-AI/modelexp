"""Two explicit backends: a local JSON mirror and the official user-identity CLI."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import tempfile
import uuid

from common import ResearchError, read_json, write_json


class UncertainWrite(ResearchError):
    """A submitted request must be reconciled before any retry."""


class FileAdapter:
    def __init__(self, path):
        self.path = Path(path)

    def snapshot(self, role, spec):
        data = read_json(self.path)['tables'][role]
        return copy.deepcopy(data['fields']), copy.deepcopy(data['records'])

    def create(self, role, spec, values):
        data = read_json(self.path)
        record_id = 'rec_' + uuid.uuid4().hex
        data['tables'][role]['records'].append({'record_id': record_id, 'fields': values})
        write_json(self.path, data)
        return record_id

    def update(self, role, spec, record_id, values):
        data = read_json(self.path)
        matches = [r for r in data['tables'][role]['records'] if r['record_id'] == record_id]
        if len(matches) != 1:
            raise ResearchError('record disappeared')
        matches[0]['fields'].update(values)
        write_json(self.path, data)

    def create_many(self, role, spec, values):
        return [self.create(role, spec, value) for value in values]

    def update_many(self, role, spec, values):
        for record_id, fields in values.items():
            self.update(role, spec, record_id, fields)

    def doctor(self):
        return {'backend': 'file', 'readable': self.path.is_file()}


class LarkAdapter:
    def __init__(self, settings, root):
        self.command = settings.get('command', ['lark-cli'])
        if not isinstance(self.command, list) or not self.command or any(not isinstance(x, str) for x in self.command):
            raise ResearchError('CLI command must be a nonempty argv array')
        self.timeout = settings.get('timeout_seconds', 60)
        self.root = Path(root) / 'cli'
        self.root.mkdir(parents=True, exist_ok=True)

    def call(self, args, cwd=None, manifest=False, write=False):
        try:
            result = subprocess.run(self.command + args, cwd=cwd, capture_output=True,
                                    text=True, timeout=self.timeout, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            error = UncertainWrite if write else ResearchError
            raise error('CLI timeout or executable failure; inspect/reconcile before retry') from exc
        if result.returncode:
            # Never echo arbitrary stderr: it may contain credentials or private payloads.
            subtype = 'cli_failure'
            try:
                subtype = json.loads(result.stderr).get('error', {}).get('subtype', subtype)
            except (ValueError, TypeError):
                pass
            error = UncertainWrite if write else ResearchError
            raise error(f'CLI failed (exit={result.returncode}, subtype={subtype})')
        try:
            body = json.loads(result.stdout)
        except ValueError as exc:
            error = UncertainWrite if write else ResearchError
            raise error('CLI returned invalid JSON') from exc
        if manifest:
            if body.get('format') != 'ndjson' or body.get('manifest_version') != 'v1':
                raise ResearchError('unexpected record export manifest')
            return body
        if body.get('ok') is not True:
            error = UncertainWrite if write else ResearchError
            raise error('CLI response did not confirm success')
        return body['data']

    def schema(self, spec):
        base, table = spec['base_token'], spec['table_id']
        fields = self.call(['base', '+field-list', '--base-token', base, '--table-id', table, '--as', 'user'])['fields']
        mapped = {rule['field_id'] for rule in spec['fields'].values()}
        for field in fields:
            if field['id'] not in mapped or field['type'] != 'select' or not (field.get('truncated') or field.get('remaining_options_count')):
                continue
            options, seen, offset, total = [], set(), 0, None
            while True:
                page = self.call(['base', '+field-search-options', '--base-token', base, '--table-id', table,
                                  '--field-id', field['id'], '--limit', '200', '--offset', str(offset), '--as', 'user'])
                entries = page.get('options', [])
                count = page.get('total')
                if not isinstance(count, int) or isinstance(count, bool) or count < 0 or (total is not None and count != total):
                    raise ResearchError('select option pagination has no stable total')
                total = count
                for entry in entries:
                    name = entry.get('name')
                    if not isinstance(name, str) or not name or name in seen:
                        raise ResearchError('duplicate or missing select option name')
                    seen.add(name)
                    options.append(entry)
                if len(options) == total:
                    break
                if not entries or len(options) > total:
                    raise ResearchError('select option pagination did not advance')
                offset += len(entries)
            field['options'] = options
            for key in ('truncated', 'remaining_options_count', 'truncated_options_count'):
                field.pop(key, None)
        return fields

    def snapshot(self, role, spec):
        fields = self.schema(spec)
        names = {f['id']: f['name'] for f in fields}
        ids = list(dict.fromkeys(f['field_id'] for f in spec['fields'].values()))
        if not set(ids) <= set(names):
            raise ResearchError('configured field ID is missing from remote schema')
        merged, expected_revision = None, None
        for start in range(0, len(ids), 50):
            records, revision = self._projection(spec, ids[start:start + 50], names)
            if merged is None:
                merged = {r['record_id']: r for r in records}
                expected_revision = revision
            else:
                if revision != expected_revision or set(merged) != {r['record_id'] for r in records}:
                    raise ResearchError('remote table changed between field projections')
                for row in records:
                    merged[row['record_id']]['fields'].update(row['fields'])
        return fields, list((merged or {}).values())

    def _projection(self, spec, ids, names):
        base, table = spec['base_token'], spec['table_id']
        records, seen, offset, revision, query = [], set(), 0, None, None
        first = True
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            while True:
                output = f'page-{offset}.ndjson'
                args = ['base', '+record-list', '--base-token', base, '--table-id', table,
                        '--offset', str(offset), '--limit', '2000', '--format', 'ndjson', '--output', output, '--as', 'user']
                for field_id in ids:
                    args.extend(['--field-id', field_id])
                meta = self.call(args, cwd=directory, manifest=True)
                if meta.get('base_token') != base or meta.get('table_id') != table or not isinstance(meta.get('has_more'), bool):
                    raise ResearchError('export target or pagination metadata mismatch')
                if first:
                    revision, query, first = meta.get('rev'), meta.get('query_context'), False
                elif meta.get('rev') != revision or meta.get('query_context') != query:
                    raise ResearchError('remote table changed during pagination; start a fresh snapshot')
                page = [json.loads(line) for line in (Path(directory) / output).read_text().splitlines() if line.strip()]
                if len(page) != meta.get('records_count'):
                    raise ResearchError('manifest row count does not match export')
                for row in page:
                    record_id = row.get('record_id')
                    if not record_id or record_id in seen:
                        raise ResearchError('duplicate or missing record_id in snapshot')
                    seen.add(record_id)
                    records.append({'record_id': record_id, 'fields': {f: row.get(names[f]) for f in ids}})
                if not meta['has_more']:
                    break
                next_offset = meta.get('next_offset')
                if not isinstance(next_offset, int) or next_offset <= offset:
                    raise ResearchError('pagination did not advance')
                offset = next_offset
        return records, revision

    def payload_call(self, command, spec, payload):
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            write_json(Path(directory) / 'request.json', payload)
            return self.call(['base', command, '--base-token', spec['base_token'], '--table-id', spec['table_id'],
                              '--json', '@request.json', '--as', 'user'], cwd=directory, write=True)

    def append_select_options(self, spec, field_id, names):
        args = ['base', '+field-get', '--base-token', spec['base_token'], '--table-id', spec['table_id'],
                '--field-id', field_id, '--as', 'user']
        current = self.call(args)['field']
        if current['type'] != 'select' or current.get('dynamic_options_source'):
            raise ResearchError('only static select options can be appended')
        complete = next(f for f in self.schema(spec) if f['id'] == field_id)
        existing = {option['name'] for option in complete['options']}
        missing = sorted(set(names) - existing)
        if not missing:
            return []
        if len(missing) > 50 or any(not isinstance(n, str) or not n.strip() or len(n) > 200 for n in missing):
            raise ResearchError('unexpected select option additions; inspect the CSV')
        body = {k: v for k, v in current.items() if k in ('name', 'type', 'multiple', 'description', 'default_value')}
        body['options'] = complete['options'] + [{'name': name} for name in missing]
        from common import digest, now
        receipt = self.root / ('options-' + digest([spec['table_id'], field_id, body]) + '.json')
        write_json(receipt, {'observed_at': now(), 'before': complete, 'request': body, 'added': missing})
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            write_json(Path(directory) / 'request.json', body)
            argv = ['base', '+field-update', '--base-token', spec['base_token'], '--table-id', spec['table_id'],
                    '--field-id', field_id, '--json', '@request.json', '--as', 'user']
            self.call(argv + ['--dry-run'], cwd=directory)
            # Explicit per-field allow_new_options authorizes append-only maintenance.
            self.call(argv + ['--yes'], cwd=directory, write=True)
        after = next(f for f in self.schema(spec) if f['id'] == field_id)
        if not existing | set(missing) <= {o['name'] for o in after['options']}:
            raise ResearchError('select option append was not verified')
        return missing

    def create(self, role, spec, values):
        result = self.payload_call('+record-batch-create', spec, {'create_records': [values]})
        ids = result.get('record_id_list', [])
        if len(ids) != 1 or not ids[0]:
            raise UncertainWrite('create succeeded without a unique record ID')
        return ids[0]

    def update(self, role, spec, record_id, values):
        result = self.payload_call('+record-batch-update', spec, {'update_records': {record_id: values}})
        if result.get('ignored_fields'):
            raise UncertainWrite('remote ignored one or more requested fields')

    def create_many(self, role, spec, values):
        result = self.payload_call('+record-batch-create', spec, {'create_records': values})
        ids = result.get('record_id_list', [])
        if len(ids) != len(values) or len(set(ids)) != len(ids) or not all(ids):
            raise UncertainWrite('batch create did not return unique IDs for every record')
        return ids

    def update_many(self, role, spec, values):
        result = self.payload_call('+record-batch-update', spec, {'update_records': values})
        if result.get('ignored_fields'):
            raise UncertainWrite('remote ignored one or more requested fields')

    def list_files(self, folder):
        files, page_token, seen = [], None, set()
        while True:
            params = {'folder_token': folder, 'page_size': 200}
            if page_token:
                params['page_token'] = page_token
            page = self.call(['drive', 'files', 'list', '--params', json.dumps(params), '--format', 'json', '--as', 'user'])
            files.extend(page.get('files', []))
            if not page.get('has_more'):
                break
            page_token = page.get('next_page_token')
            if not page_token or page_token in seen:
                raise ResearchError('Drive pagination did not advance')
            seen.add(page_token)
        return files

    def download(self, token, destination):
        destination = Path(destination)
        result = self.call(['drive', '+download', '--file-token', token, '--output', destination.name, '--as', 'user'], cwd=destination.parent)
        if not destination.is_file() or Path(result['saved_path']).resolve() != destination.resolve():
            raise ResearchError('download did not produce the requested file')

    def doctor(self):
        # auth status has a management-specific contract rather than an ok/data envelope.
        try:
            r = subprocess.run(self.command + ['auth', 'status', '--json', '--verify'], capture_output=True,
                               text=True, timeout=self.timeout, check=False)
            s = json.loads(r.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            raise ResearchError('cannot verify CLI user identity') from exc
        user = s.get('identities', {}).get('user', {})
        return {'backend': 'lark', 'identity': s.get('identity'), 'verified': user.get('verified', False),
                'status': user.get('status'), 'token_status': user.get('tokenStatus'),
                'refresh_expires_at': user.get('refreshExpiresAt')}


def adapter_for(cfg):
    backend = cfg.get('backend', {})
    if backend.get('kind') == 'file':
        return FileAdapter(backend['path'])
    if backend.get('kind') == 'lark':
        return LarkAdapter(backend, cfg['_state'])
    raise ResearchError('backend.kind must be file or lark')
