"""Strict identity and field value normalization; ambiguity is never name-matched away."""
from datetime import datetime
import math
import re
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from common import ResearchError, digest

READONLY_TYPES = {'formula', 'lookup', 'created_at', 'updated_at', 'created_by', 'updated_by', 'auto_number'}


def url_identity(value, preferred_host=None, first=False):
    if not isinstance(value, str):
        raise ResearchError('identity URL must be text')
    # Accept a bare URL or one unambiguous URL embedded in a CSV source cell.
    value = re.sub(r'\[[^\]]+\]\((https?://[^)]+)\)', r'\1', value)
    urls = re.findall(r'https?://[^\s；;<>]+', value)
    urls = list(dict.fromkeys(u.rstrip('。,') for u in urls))
    if len(urls) > 1 and preferred_host:
        preferred = [url for url in urls if urlsplit(url).hostname == preferred_host]
        if preferred or not first:
            urls = preferred
    if len(urls) > 1 and first:
        urls = urls[:1]
    if len(urls) != 1:
        raise ResearchError('identity URL is missing or ambiguous')
    parts = urlsplit(urls[0])
    if not parts.hostname or parts.username or parts.password:
        raise ResearchError('invalid identity URL')
    host = parts.hostname.lower()
    port = parts.port
    host = '[' + host + ']' if ':' in host else host
    default_port = 443 if parts.scheme.lower() == 'https' else 80
    netloc = host + (f':{port}' if port and port != default_port else '')
    return urlunsplit((parts.scheme.lower(), netloc, parts.path.rstrip('/') or '/', parts.query, ''))


def normalize(value, field):
    if value is None:
        return None
    kind = field['type']
    if kind == 'text':
        if not isinstance(value, str):
            raise ResearchError('text value must be a string')
        value = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', lambda m: m[1] if m[1] == m[2] else m[0], value)
        return value.replace('\r\n', '\n')
    if kind == 'select':
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            raise ResearchError('select value must be an array of option names')
        if not field.get('multiple') and len(value) > 1:
            raise ResearchError('single select has multiple values')
        allowed = {x['name'] for x in field.get('options', [])}
        if not set(value) <= allowed:
            raise ResearchError('select value contains unknown options')
        return sorted(set(value))
    if kind == 'number':
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ResearchError('number must be finite; unknown is not zero')
        return value
    if kind == 'datetime':
        if not isinstance(value, str):
            raise ResearchError('datetime must be an ISO string with an explicit business date or timezone')
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            value += 'T00:00:00+08:00'
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ResearchError('datetime timezone is required')
        return dt.astimezone(ZoneInfo('UTC')).isoformat()
    if kind == 'checkbox' and isinstance(value, bool):
        return value
    raise ResearchError('unsupported writable field type: ' + kind)


def source_value(value, field, rule=None):
    if value == '':
        return None
    rule = rule or {}
    if rule.get('identity_url') and field.get('style', {}).get('type') == 'url':
        # A URL cell accepts one link, not the CSV's repository label plus link.
        value = url_identity(value, rule.get('identity_preferred_host'), rule.get('identity_url_first', False))
        if urlsplit(value).path == '/' and not urlsplit(value).query:
            value = value[:-1]
    if field['type'] == 'select':
        aliases = rule.get('value_aliases', {})
        value = aliases.get(value.strip(), value.strip())
        allowed = {x['name'] for x in field.get('options', [])}
        if value in allowed or not field.get('multiple'):
            value = [value]
        else:
            parts = [aliases.get(v.strip(), v.strip()) for v in re.split(r'[,，、;；／]', value) if v.strip()]
            value = []
            for part in parts:
                # Preserve registered names such as C++, HumanEval+ and 文本+图像输入.
                # A new separator is unambiguous only when every piece is a known option.
                pieces = [aliases.get(v.strip(), v.strip()) for v in re.split(r'[+＋]', part)]
                value.extend(pieces if part not in allowed and len(pieces) > 1
                             and all(v in allowed for v in pieces) else [part])
    elif field['type'] == 'number':
        try:
            value = float(value)
        except ValueError as exc:
            raise ResearchError('invalid numeric CSV value') from exc
    elif field['type'] == 'checkbox':
        if value.lower() not in ('true', 'false'):
            raise ResearchError('invalid checkbox CSV value')
        value = value.lower() == 'true'
    return normalize(value, field)


def identity(role, spec, values):
    parts = []
    for key in spec['identity']:
        value = values.get(key)
        if value is None or value == '' or value == []:
            raise ResearchError(f'{role}: missing identity field {key}')
        if spec['fields'][key].get('identity_url'):
            value = url_identity(value, spec['fields'][key].get('identity_preferred_host'),
                                 spec['fields'][key].get('identity_url_first', False))
        parts.append([key, value])
    return role + '_' + digest(parts)[:24], parts


def resolve_fields(spec, schema):
    fields = {f['id']: f for f in schema}
    resolved = {}
    for key, rule in spec['fields'].items():
        actual = fields.get(rule['field_id'])
        if not actual or actual['type'] != rule['type']:
            raise ResearchError('schema changed for mapped field: ' + key)
        resolved[key] = actual
    return resolved
