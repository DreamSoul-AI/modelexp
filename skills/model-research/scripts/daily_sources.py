"""Read bounded public release feeds and pin every researched repository."""
from datetime import datetime, timedelta
import json
import re
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener
import xml.etree.ElementTree as ET

from common import ResearchError
from daily_history import entity_keys, has_history_match
from score_sources import PublicRedirects, fetch_text, public_url


HF = 'https://huggingface.co'
GH = 'https://api.github.com'
REPO = re.compile(r'[\w.-]+/[\w.-]+\Z')
REVISION = re.compile(r'[0-9a-f]{40}\Z')
QUANT = re.compile(r'(?:gguf|gptq|awq|exl2|int[48]|mlx|nvfp4|mxfp4|bitsandbytes)', re.I)
NETWORK_ERRORS = (OSError, ValueError, ResearchError, ET.ParseError, KeyError, TypeError)


def get(url, params=()):
    url += '?' + urlencode(params, doseq=True) if params else ''
    request = Request(public_url(url), headers={'User-Agent': 'ModelExp/0.9 public release reader'})
    with build_opener(PublicRedirects()).open(request, timeout=20) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ResearchError('release feed exceeds its read limit')
    return raw


def hf_rows(kind, **filters):
    return json.loads(get(f'{HF}/api/{kind}', {'sort': 'createdAt', 'direction': -1, 'limit': 45, **filters}))


def github_rows(since):
    search = 'benchmark in:name,description created:>=' + since.date().isoformat()
    result = json.loads(get(GH + '/search/repositories', {'q': search, 'sort': 'updated', 'per_page': 45}))
    if result.get('incomplete_results'):
        raise ResearchError('GitHub search response was incomplete')
    return result['items']


def arxiv_links(since):
    candidates = set()
    count = 0
    for category in ('cs.CL', 'cs.LG'):
        root = ET.fromstring(get('https://rss.arxiv.org/rss/' + category))
        for item in root.findall('./channel/item'):
            description = item.findtext('description', '')
            if not re.search(r'language model|benchmark|quantization', description, re.I):
                continue
            count += 1
            for url in re.findall(r'https://(?:github\.com|huggingface\.co/(?:datasets/)?)[^\s<>"\])},]+', description):
                url = url.rstrip('.')
                match = re.match(r'https://(github\.com|huggingface\.co)/(datasets/)?([\w.-]+/[\w.-]+)', url)
                if match:
                    domain, dataset, repo = match.groups()
                    candidates.add((domain, bool(dataset), repo))
    return sorted(candidates), count


def created_after(value, since):
    return datetime.fromisoformat(value.replace('Z', '+00:00')) >= since


def scan(since, history):
    candidates, coverage, seen = [], {}, set()

    def collect(key, fn, convert):
        try:
            rows = fn()
            entries = [item for row in rows if (item := convert(row))]
            for role, domain, repo in entries:
                url = (HF + '/datasets/' if domain == 'dataset' else
                       'https://github.com/' if domain == 'github' else HF + '/') + repo
                identity = (role, domain, repo.casefold())
                if not REPO.fullmatch(repo) or identity in seen:
                    continue
                seen.add(identity)
                keys = entity_keys(role, repo.rsplit('/', 1)[1], url)
                if role != 'artifacts' and history[role] & keys:
                    continue
                if role == 'artifacts' and 'repo:' + repo.casefold() in history[role]:
                    continue
                candidates.append({'role': role, 'domain': domain, 'repo': repo, 'url': url, 'feed': key})
            coverage[key] = {'status': 'scanned', 'listed': len(rows), 'candidates': len(entries), 'limit': 45}
        except NETWORK_ERRORS as exc:
            coverage[key] = {'status': 'unavailable', 'reason': type(exc).__name__}

    def hf_candidate(row, role, domain):
        if row.get('private') or row.get('gated') or not created_after(row['createdAt'], since):
            return None
        return role, domain, row['id']

    collect('hf_models', lambda: hf_rows('models', filter='text-generation'),
            lambda r: hf_candidate(r, 'artifacts' if QUANT.search(r['id']) else 'models', 'model'))
    collect('hf_multimodal', lambda: hf_rows('models', filter='image-text-to-text'),
            lambda r: hf_candidate(r, 'artifacts' if QUANT.search(r['id']) else 'models', 'model'))
    for label, pipeline in (('hf_audio', 'automatic-speech-recognition'), ('hf_tts', 'text-to-speech'),
                            ('hf_vision', 'image-classification'), ('hf_image', 'text-to-image'), ('hf_video', 'text-to-video')):
        collect(label, lambda: hf_rows('models', filter=pipeline),
                lambda r: hf_candidate(r, 'artifacts' if QUANT.search(r['id']) else 'models', 'model'))
    collect('hf_datasets', lambda: hf_rows('datasets', search='bench'),
            lambda r: hf_candidate(r, 'benchmarks', 'dataset'))
    collect('hf_quant', lambda: hf_rows('models', filter='gguf'),
            lambda r: hf_candidate(r, 'artifacts', 'model'))
    collect('github_benchmarks', lambda: github_rows(since),
            lambda r: ('benchmarks', 'github', r['full_name']) if not r['fork'] else None)

    def arxiv_candidate(item):
        domain, dataset, repo = item
        if domain == 'github':
            return ('benchmarks', 'github', repo) if re.search('bench|eval', repo, re.I) else None
        if dataset:
            return 'benchmarks', 'dataset', repo
        return ('artifacts' if QUANT.search(repo) else 'models', 'model', repo)

    def paper_releases():
        links, count = arxiv_links(since)
        coverage['arxiv_abstracts'] = {'status': 'scanned', 'relevant_abstracts': count, 'feeds': ['cs.CL', 'cs.LG']}
        return links

    collect('arxiv_linked_releases', paper_releases, arxiv_candidate)
    return candidates, coverage


def pinned_source(item):
    domain, repo = item['domain'], item['repo']
    repo_path = quote(repo, safe='/')
    if domain == 'github':
        entry = json.loads(get(f'{GH}/repos/{repo_path}'))
        branch = quote(entry['default_branch'], safe='')
        revision = json.loads(get(f'{GH}/repos/{repo_path}/commits/{branch}'))['sha']
        source = f'{GH}/repos/{repo_path}/readme?ref={revision}'
        metadata = {key: entry.get(key) for key in ('description', 'license', 'created_at', 'topics')}
    else:
        kind = 'datasets' if domain == 'dataset' else 'models'
        entry = json.loads(get(f'{HF}/api/{kind}/{repo_path}', {'expand': ['sha', 'cardData', 'pipeline_tag', 'createdAt', 'safetensors', 'tags']})) if domain != 'dataset' else json.loads(get(f'{HF}/api/datasets/{repo_path}'))
        revision = entry['sha']
        source = f"{HF}/{'datasets/' if domain == 'dataset' else ''}{repo_path}/raw/{revision}/README.md"
        metadata = {key: entry.get(key) for key in ('cardData', 'pipeline_tag', 'createdAt', 'safetensors', 'tags')}
    if not REVISION.fullmatch(revision):
        raise ResearchError('primary revision could not be pinned')
    evidence = fetch_text(source)
    return {**item, 'id': item['role'] + ':' + repo.casefold(), 'revision': revision,
            'source': source, 'excerpt': evidence['text'][:6500], 'source_sha256': evidence['source_sha256'],
            'truncated': evidence['truncated'] or len(evidence['text']) > 6500, 'metadata': metadata}


def quant_files(item, history):
    data = item['metadata'].get('cardData') or {}
    base = data.get('base_model')
    if isinstance(base, list):
        base = base[0] if len(base) == 1 else None
    if not isinstance(base, str) or not REPO.fullmatch(base) or base.casefold() == item['repo'].casefold():
        return []
    base_info = json.loads(get(f'{HF}/api/models/{quote(base, safe="/")}', {'expand': 'sha'}))
    if not REVISION.fullmatch(base_info.get('sha') or ''):
        return []
    repo_path = quote(item['repo'], safe='/')
    api = f"{HF}/api/models/{repo_path}/tree/{item['revision']}"
    rows = json.loads(get(api, {'recursive': 'true'}))
    files = []
    for row in rows:
        name = row['path']
        lfs = row.get('lfs') or {}
        if row.get('type') != 'file' or not name.lower().endswith('.gguf') or not lfs.get('oid') or not lfs.get('size'):
            continue
        url = f"{item['url']}/resolve/{item['revision']}/{quote(name, safe='/')}"
        if has_history_match(entity_keys('artifacts', name, url), history):
            continue
        files.append({'name': name, 'url': url, 'size': lfs['size'], 'sha256': lfs['oid'], 'base': base, 'source': api})
    return sorted(files, key=lambda f: f['name'])[:4]
