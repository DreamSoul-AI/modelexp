"""Build the publication deduplication index from Base and prior deliveries."""
import csv
import io
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit, urlunsplit

from common import ResearchError, digest, read_json, write_json
from ingest import columns_for, input_folder


IDENTITY_COLUMNS = {
    'models': ('模型名称', '获取地址'),
    'benchmarks': ('名称', '官方地址'),
    'artifacts': ('制品或产物', '制品入口'),
}
REPO_COMPONENT = re.compile(r'[\w.-]+\Z')
DOC_ID = re.compile(r'(models|benchmarks)_([\w.-]+)__([\w.-]+)_[0-9a-f]{7,40}\.md\Z', re.I)


def normalized_name(value):
    if isinstance(value, list):
        value = ' '.join(segment.get('text', '') for segment in value if isinstance(segment, dict))
    if not isinstance(value, str):
        return ''
    return ''.join(c for c in unicodedata.normalize('NFKC', value).casefold().removesuffix('.gguf') if c.isalnum())


def link_keys(value, role):
    if isinstance(value, dict):
        value = value.get('link') or value.get('url') or value.get('text')
    if isinstance(value, list):
        return set().union(*(link_keys(item, role) for item in value))
    if not isinstance(value, str):
        return set()
    keys = set()
    for url in re.findall(r'https?://[^\s；;<>"\[\]()，]+', value):
        parts = urlsplit(url.rstrip('。,'))
        host = parts.hostname
        path = [unquote(part).casefold() for part in parts.path.split('/') if part]
        if host in ('hf.co', 'huggingface.co'):
            dataset = path[:1] == ['datasets']
            repo_path = path[1:] if dataset else path
            if len(repo_path) >= 2 and all(REPO_COMPONENT.fullmatch(p) for p in repo_path[:2]):
                repo = '/'.join(repo_path[:2])
                if role == 'artifacts' and len(repo_path) >= 5 and repo_path[2] in ('resolve', 'blob', 'raw'):
                    keys.add('file:' + repo + '/' + '/'.join(repo_path[4:]))
                else:
                    keys.add('repo:' + repo)
                continue
        if host in ('github.com', 'www.github.com', 'api.github.com', 'raw.githubusercontent.com'):
            if host == 'api.github.com' and path[:1] == ['repos']:
                path = path[1:]
            if len(path) >= 2 and all(REPO_COMPONENT.fullmatch(p) for p in path[:2]):
                keys.add('repo:' + path[0] + '/' + path[1].removesuffix('.git'))
                continue
        if host in ('arxiv.org', 'www.arxiv.org') and len(path) >= 2:
            keys.add('paper:' + re.sub(r'v\d+$', '', '/'.join(path[1:]).removesuffix('.pdf')))
        elif host:
            keys.add('url:' + urlunsplit(('', host.removeprefix('www.'), parts.path.rstrip('/'), '', '')))
    return keys


def entity_keys(role, name, source):
    keys = link_keys(source, role)
    name = normalized_name(name)
    if name:
        keys.add('name:' + name)
    return keys


def row_keys(role, row):
    name, source = IDENTITY_COLUMNS[role]
    return entity_keys(role, row.get(name), row.get(source))


def has_history_match(keys, previous):
    return bool(keys & previous) or any(key.startswith('file:') and 'repo:' + '/'.join(key[5:].split('/', 2)[:2]) in previous
                                        for key in keys)


def history_file_rows(role, data):
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
    if not set(IDENTITY_COLUMNS[role]) <= set(reader.fieldnames or []):
        raise ResearchError('historical ' + role + ' file is missing name or source column')
    return [row_keys(role, row) for row in reader]


def collect_history(cfg, drive, cache, day):
    index = {role: set() for role in IDENTITY_COLUMNS}
    counts = {}
    for role, keys in index.items():
        spec = cfg['roles'][role]
        rules = spec['fields']
        name = rules['name']['field_id']
        source = rules['source_url']['field_id']
        _, rows = drive.snapshot(role, spec)
        for row in rows:
            values = row['fields']
            keys.update(entity_keys(role, values.get(name), values.get(source)))
        counts[role] = {'base_records': len(rows), 'historical_files': 0}
        pattern = re.escape(spec['input']['filename']).replace(re.escape('{date}'), r'(\d{4}-\d{2}-\d{2})')
        for item in drive.list_files(input_folder(spec['input'], drive)):
            match = re.fullmatch(pattern, item['name'])
            if item['type'] != 'file' or not match or match[1] >= day:
                continue
            cache_path = cache / (digest([item['token'], item.get('modified_time')]) + '.json')
            if item.get('modified_time') and cache_path.is_file():
                rows = read_json(cache_path)
            else:
                with tempfile.TemporaryDirectory(dir=cache) as temp:
                    path = Path(temp) / 'source.csv'
                    drive.download(item['token'], path)
                    rows = [sorted(keys) for keys in history_file_rows(role, path.read_bytes())]
                if item.get('modified_time'):
                    write_json(cache_path, rows)
            for previous in rows:
                keys.update(previous)
            counts[role]['historical_files'] += 1
    source = cfg['roles']['models']['input']
    parent = source.get('root_folder_token') or source['folder_token']
    roots = [item for item in drive.list_files(parent) if item['name'] == 'md' and item['type'] == 'folder']
    if len(roots) != 1:
        raise ResearchError('daily Markdown root is missing or ambiguous')
    pending = [roots[0]['token']]
    while pending:
        for item in drive.list_files(pending.pop()):
            if item['type'] == 'folder':
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', item['name']) or item['name'] < day:
                    pending.append(item['token'])
            elif item['type'] == 'file' and (hit := DOC_ID.fullmatch(item['name'])):
                index[hit[1].lower()].add('repo:' + hit[2].casefold() + '/' + hit[3].casefold())
    return index, counts


def channel_snapshot(cfg, drive, folder, day):
    spec = cfg['roles']['channels']
    source = spec['input']
    pattern = re.escape(source['filename']).replace(re.escape('{date}'), r'(\d{4}-\d{2}-\d{2})')
    prior = []
    for item in drive.list_files(input_folder(source, drive)):
        match = re.fullmatch(pattern, item['name'])
        if item['type'] == 'file' and match and match[1] < day:
            prior.append((match[1], item['token']))
    if not prior:
        raise ResearchError('no prior channel roster to carry forward')
    latest = max(stamp for stamp, _ in prior)
    tokens = [token for stamp, token in prior if stamp == latest]
    if len(tokens) != 1:
        raise ResearchError('prior channel roster is ambiguous')
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        path = Path(temp) / 'channels.csv'
        drive.download(tokens[0], path)
        return path.read_bytes()
