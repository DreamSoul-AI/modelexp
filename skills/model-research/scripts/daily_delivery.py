#!/usr/bin/env python3
"""Check a Codex-produced daily bundle and deliver it without overwriting other producers."""
import argparse
from collections import Counter
import csv
from datetime import date
import fcntl
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile

from common import ResearchError, digest, load_config, now, read_json, write_json
from identity import identity, resolve_fields, source_value
from ingest import columns_for, input_folder
from lark_adapter import LarkAdapter, UncertainWrite, adapter_for


ASSETS = Path(__file__).resolve().parents[1] / 'assets'
ROLES = ('models', 'benchmarks', 'channels', 'artifacts')
SOURCE_LINKS = 'channel/source_links_{date}.csv'
DOC_NAME = re.compile(r'(?:models|benchmarks)_[\w.-]+__[\w.-]+_[0-9a-f]{7,40}\.md', re.I)


def csv_rows(path, headers):
    data = path.read_bytes()
    if not data.startswith(b'\xef\xbb\xbf'):
        raise ResearchError('UTF-8 BOM required: ' + path.name)
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
    if reader.fieldnames != headers:
        raise ResearchError('header or field order differs: ' + path.name)
    rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ResearchError('incorrect row width: ' + path.name)
    return rows


def verify_rows(role, rows, headers, spec, schema):
    fields = resolve_fields(spec, schema)
    columns = {key: columns_for(rule, headers) for key, rule in spec['fields'].items() if rule.get('column')}
    seen, new_options = set(), set()
    for lineno, row in enumerate(rows, 2):
        values = {key: row[column] for key, column in columns.items()}
        try:
            key, _ = identity(role, spec, values)
            if key in seen:
                raise ResearchError('duplicate entity identity')
            seen.add(key)
            for key, text in values.items():
                rule = spec['fields'][key]
                field = fields[key]
                if not text or rule.get('policy') != 'ai' or not rule.get('accept_upstream'):
                    continue
                if rule.get('allow_new_options') and field['type'] == 'select' and not field.get('multiple'):
                    value = rule.get('value_aliases', {}).get(text.strip(), text.strip())
                    if value not in {opt['name'] for opt in field['options']}:
                        if not value or len(value) > 200:
                            raise ResearchError('invalid new option in ' + columns[key])
                        new_options.add((key, value))
                    continue
                source_value(text, field, rule)
        except (ResearchError, ValueError, TypeError) as exc:
            raise ResearchError(f'{role} CSV row {lineno}: {exc}') from exc
    limits = Counter(key for key, _ in new_options)
    if any(count > 50 for count in limits.values()):
        raise ResearchError(role + ' delivery contains too many new select options')
    return dict(limits)


def file_receipt(path, root, rows=None):
    return {'path': path.relative_to(root).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            **({'rows': rows} if rows is not None else {})}


def verify_bundle(cfg, drive, root, day):
    templates = read_json(ASSETS / 'daily-delivery-columns.json')
    roots, receipts, table_counts, options = {}, [], {}, {}
    for role in ROLES:
        spec = cfg['roles'][role]
        source = spec['input']
        relative = '/'.join(source['subdirectory'] + [source['filename']])
        headers = templates[relative]
        folder = input_folder(source, drive)
        path = root / relative.format(date=day)
        if role == 'artifacts' and not path.exists() and source.get('required') is False:
            continue
        rows = csv_rows(path, headers)
        if not rows:
            raise ResearchError('header-only CSV needs an explicit completion handoff: ' + path.name)
        options[role] = verify_rows(role, rows, headers, spec, drive.schema(spec))
        table_counts[role] = len(rows)
        roots[source['subdirectory'][0]] = folder
        receipts.append(file_receipt(path, root, len(rows)))
    path = root / SOURCE_LINKS.format(date=day)
    links = csv_rows(path, templates[SOURCE_LINKS])
    channel_ids = {row['渠道ID'] for row in csv_rows(root / f'channel/channels_{day}.csv',
                                                   templates['channel/channels_{date}.csv'])}
    ids_seen = set()
    for link in links:
        key = tuple(link[k] for k in ('对象类型', '对象ID', '渠道ID', '证据链接'))
        if not all(key) or key in ids_seen or link['渠道ID'] not in channel_ids:
            raise ResearchError('duplicate or unlinked source evidence')
        if not link['证据链接'].startswith('https://'):
            raise ResearchError('source evidence must use a public HTTPS link')
        date.fromisoformat(link['发现时间'])
        ids_seen.add(key)
    receipts.append(file_receipt(path, root, len(links)))

    md_files = sorted((root / 'md' / day).glob('*.md'))
    if not md_files:
        raise ResearchError('daily Markdown folder is empty')
    for path in md_files:
        if not DOC_NAME.fullmatch(path.name):
            raise ResearchError('unexpected Markdown filename: ' + path.name)
        content = path.read_text(encoding='utf-8')
        if len(re.findall(r'^# ', content, re.M)) != 1 or '## 来源与阅读范围' not in content or day not in content:
            raise ResearchError('Markdown must include one title, business date and sources: ' + path.name)
        if not re.search(r'\[S\d+\].*https://', content):
            raise ResearchError('Markdown has no cited HTTPS source: ' + path.name)
        receipts.append(file_receipt(path, root))
    return {'business_date': day, 'checked_at': now(), 'files': receipts, 'table_rows': table_counts,
            'source_links': len(links), 'markdown_files': len(md_files), 'new_select_options': options}, roots


def unique_item(drive, folder, name, kind):
    matches = [f for f in drive.list_files(folder) if f['name'] == name]
    if len(matches) > 1 or matches and matches[0]['type'] != kind:
        raise ResearchError('ambiguous Drive target: ' + name)
    return matches[0] if matches else None


def readback(drive, item, path):
    if path.suffix == '.md':
        payload = drive.markdown_fetch(item['token']).encode()
    else:
        with tempfile.TemporaryDirectory(dir=drive.root) as tmp:
            destination = Path(tmp) / 'verify.csv'
            drive.download(item['token'], destination)
            payload = destination.read_bytes()
    return hashlib.sha256(payload).hexdigest()


def publish(cfg, drive, root, report, roots, journal):
    day = report['business_date']
    source = cfg['roles']['models']['input']
    parent = source.get('root_folder_token') or source.get('folder_token')
    md = unique_item(drive, parent, 'md', 'folder')
    if md is None:
        raise ResearchError('confirmed md root is missing')
    md_day = unique_item(drive, md['token'], day, 'folder')
    entries = {}
    for f in report['files']:
        path = root / f['path']
        folder = (md_day or {}).get('token') if path.suffix == '.md' else roots[Path(f['path']).parts[0]]
        item = unique_item(drive, folder, path.name, 'file') if folder else None
        if item and readback(drive, item, path) != f['sha256']:
            raise ResearchError('existing file differs; resolve producer overlap: ' + f['path'])
        if not item and f['path'] in journal['pending']:
            raise UncertainWrite('previous submission not found; reconcile before creating: ' + f['path'])
        entries[f['path']] = item
    if md_day is None:
        if 'md/' + day in journal['pending']:
            raise UncertainWrite('previous folder submission not visible')
        journal['pending'].append('md/' + day)
        write_json(journal['path'], journal)
        drive.call(['drive', '+create-folder', '--name', day, '--folder-token', md['token'], '--as', 'user'], write=True)
        md_day = unique_item(drive, md['token'], day, 'folder')
        if not md_day:
            raise UncertainWrite('new date folder not confirmed')
        journal['pending'].remove('md/' + day)
        write_json(journal['path'], journal)
    for f in report['files']:
        relative = f['path']
        path = root / relative
        folder = md_day['token'] if path.suffix == '.md' else roots[Path(relative).parts[0]]
        item = entries[relative]
        if not item:
            item = unique_item(drive, folder, path.name, 'file')
        if item and readback(drive, item, path) != f['sha256']:
            raise ResearchError('concurrent file differs: ' + relative)
        if not item:
            if file_receipt(path, root)['sha256'] != f['sha256']:
                raise ResearchError('local file changed after validation: ' + relative)
            journal['pending'].append(relative)
            write_json(journal['path'], journal)
            domain, command = ('markdown', '+create') if path.suffix == '.md' else ('drive', '+upload')
            drive.call([domain, command, '--folder-token', folder, '--file', path.name, '--as', 'user'],
                       cwd=path.parent, write=True)
            item = unique_item(drive, folder, path.name, 'file')
            if not item or readback(drive, item, path) != f['sha256']:
                raise UncertainWrite('uploaded file readback differs: ' + relative)
        journal['verified'][relative] = {'sha256': f['sha256'], 'token': item['token'], 'url': item.get('url')}
        if relative in journal['pending']:
            journal['pending'].remove(relative)
        write_json(journal['path'], journal)
    return journal['verified']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['check', 'publish'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--date', required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    day = date.fromisoformat(args.date).isoformat()
    cfg = load_config(args.config)
    drive = adapter_for(cfg)
    if not isinstance(drive, LarkAdapter):
        raise ResearchError('delivery requires the live Feishu schema')
    root = args.bundle.resolve()
    report, roots = verify_bundle(cfg, drive, root, day)
    if args.mode == 'publish':
        coverage = read_json(root / 'coverage.json')
        if coverage.get('business_date') != day or coverage.get('status') != 'accepted':
            raise ResearchError('publish requires an accepted daily coverage review')
        if not cfg.get('allow_writes'):
            raise ResearchError('publish requires the authorized write configuration')
        state_dir = Path(cfg['_state']) / 'delivery'
        state_dir.mkdir(mode=0o700, exist_ok=True)
        journal_path = state_dir / (day + '.json')
        with (state_dir / 'publish.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            journal = read_json(journal_path) if journal_path.exists() else {'pending': [], 'verified': {}}
            current_digest = digest(report['files'])
            if journal.get('bundle_sha256', current_digest) != current_digest:
                raise ResearchError('a different bundle has an existing journal for this date')
            journal.update(path=str(journal_path), bundle_sha256=current_digest)
            report['published'] = publish(cfg, drive, root, report, roots, journal)
    write_json(root / 'delivery-check.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ResearchError, csv.Error, OSError, ValueError, KeyError) as exc:
        raise SystemExit(str(exc))
