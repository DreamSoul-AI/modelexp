"""Fetch bounded public source text before asking an Agent to synthesize claims."""
import base64
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

from common import ResearchError, digest, now
from identity import url_identity

MAX_BYTES = 1024 * 1024
MAX_TEXT = 18000


def public_url(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        raise ResearchError('research sources require public HTTPS URLs without credentials')
    if parts.hostname.lower() in ('localhost', 'metadata.google.internal'):
        raise ResearchError('local endpoints are not public sources')
    try:
        if not ipaddress.ip_address(parts.hostname).is_global:
            raise ResearchError('private IP is not a research source')
    except ValueError:
        pass
    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ResearchError('source DNS lookup failed') from exc
    if any(not ipaddress.ip_address(entry[4][0]).is_global for entry in addresses):
        raise ResearchError('source resolves to a private address')
    return url


class PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        elif tag in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3') and not self.hidden:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def source_urls(item, roles):
    spec = roles[item['role']]
    parts = dict(item['identity'])
    keys = [k for k in spec['identity'] if spec['fields'][k].get('identity_url')]
    if not keys:
        return []
    primary = public_url(url_identity(parts[keys[0]]))
    url = urlsplit(primary)
    path = [x for x in url.path.split('/') if x]
    revision = item.get('raw_fields', {}).get('revision', '')
    hit = re.search(r'(?:^|@|=)([a-fA-F0-9]{7,40})(?:$|[\s;])', revision)
    revision = hit[1] if hit else 'main'
    if url.hostname in ('huggingface.co', 'hf.co'):
        is_dataset = path and path[0] == 'datasets'
        repo = path[1:3] if is_dataset else path[:2]
        if len(repo) == 2 and repo[0] not in ('api', 'docs', 'spaces'):
            prefix = 'datasets/' if is_dataset else ''
            name = '/'.join(quote(x, safe='') for x in repo)
            return [f'https://huggingface.co/{prefix}{name}/raw/{revision}/README.md', primary]
    if url.hostname == 'github.com' and len(path) >= 2:
        name = '/'.join(quote(x, safe='') for x in path[:2])
        suffix = '?ref=' + revision if revision != 'main' else ''
        return [f'https://api.github.com/repos/{name}/readme{suffix}', primary]
    return [primary]


def fetch_text(url):
    public_url(url)
    request = Request(url, headers={'User-Agent': 'ModelResearch/0.3 public-source-reader',
                                    'Accept': 'text/plain,text/html,application/json'})
    with build_opener(PublicRedirects()).open(request, timeout=20) as response:
        public_url(response.geturl())
        if urlsplit(response.geturl()).path.rstrip('/') in ('/login', '/signin', '/sign-in'):
            raise ResearchError('source requires login')
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ResearchError('source exceeds one MiB reading limit')
        kind = response.headers.get_content_type()
        if kind not in ('text/plain', 'text/html', 'application/json', 'text/markdown', 'application/octet-stream'):
            raise ResearchError('source is not readable text')
        text = raw.decode('utf-8', errors='replace')
        if urlsplit(url).hostname == 'api.github.com' and kind == 'application/json':
            data = json.loads(text)
            if data.get('encoding') == 'base64' and isinstance(data.get('content'), str):
                text = base64.b64decode(data['content'], validate=False).decode('utf-8', errors='replace')
        if kind == 'text/html':
            parser = PageText()
            parser.feed(text)
            text = '\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
        if not text.strip():
            raise ResearchError('source text is empty')
        return {'text': text[:MAX_TEXT], 'truncated': len(text) > MAX_TEXT,
                'source_sha256': hashlib.sha256(raw).hexdigest(), 'url': url}


def collect(request, fetch=fetch_text):
    evidence, failures = [], []
    for item in request['entities']:
        try:
            urls = source_urls(item, request['roles'])
        except (ResearchError, ValueError) as exc:
            failures.append({'entity_id': item['entity_id'], 'reason': str(exc)})
            continue
        for url in urls:
            try:
                source = fetch(url)
                entry = {'evidence_id': 'src_' + digest([item['entity_id'], source['url'], source['text']])[:20],
                         'url': source['url'], 'kind': 'source_statement', 'excerpt': source['text'],
                         'observed_at': now(), 'entity_id': item['entity_id'], 'source_sha256': source['source_sha256'],
                         'read_scope': f"至多{MAX_TEXT}字符；truncated={source['truncated']}"}
                evidence.append(entry)
                break
            except (HTTPError, URLError, OSError, ResearchError, ValueError) as exc:
                reason = 'HTTP ' + str(exc.code) if isinstance(exc, HTTPError) else type(exc).__name__
                failures.append({'entity_id': item['entity_id'], 'url': url, 'reason': reason})
        if not urls:
            failures.append({'entity_id': item['entity_id'], 'reason': 'no configured public source'})
    return evidence, failures
