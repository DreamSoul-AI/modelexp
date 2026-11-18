"""Small serialization/configuration helpers; no service credentials are stored here."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
from datetime import datetime
from zoneinfo import ZoneInfo


class ResearchError(Exception):
    """An actionable input, policy, or runtime error."""


def now():
    return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def run_process(command, *, timeout, cwd=None, input=None, env=None):
    """Stop the whole child job on timeout or service termination, including grandchildren."""
    child = subprocess.Popen(command, cwd=cwd, env=env, text=True,
                             stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    previous = None
    def terminate(*_):
        raise SystemExit(143)
    if threading.current_thread() is threading.main_thread():
        previous = signal.signal(signal.SIGTERM, terminate)
    try:
        stdout, stderr = child.communicate(input=input, timeout=timeout)
        return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
    finally:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()
        if previous is not None:
            signal.signal(signal.SIGTERM, previous)


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def inside(root, *parts):
    root = Path(root).resolve()
    result = root.joinpath(*parts).resolve()
    if not result.is_relative_to(root):
        raise ResearchError('path escapes the configured state directory')
    return result


def load_config(path):
    path = Path(path).resolve()
    cfg = read_json(path)
    if cfg.get('schema_version') != 1 or not isinstance(cfg.get('roles'), dict) or not cfg['roles']:
        raise ResearchError('config requires schema_version=1 and nonempty roles')
    for key in ('allow_writes', 'allow_unconfirmed_input'):
        if key in cfg and not isinstance(cfg[key], bool):
            raise ResearchError(key + ' must be a JSON boolean')
    size = cfg.get('backend', {}).get('batch_size', 1)
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 200:
        raise ResearchError('backend.batch_size must be between 1 and 200')
    readiness = cfg.get('input_readiness', {})
    if readiness:
        interval = readiness.get('min_interval_seconds')
        if readiness.get('strategy') != 'stable_observations' or isinstance(interval, bool) or not isinstance(interval, (int, float)) or not 60 <= interval <= 3600:
            raise ResearchError('stable_observations requires min_interval_seconds between 60 and 3600')
    state = (path.parent / cfg['state_dir']).resolve()
    checkout = Path(__file__).resolve().parents[3]
    if state.is_relative_to(checkout):
        raise ResearchError('state_dir must be outside the checkout')
    for role, spec in cfg['roles'].items():
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,39}', role):
            raise ResearchError('invalid role name')
        if not spec.get('fields') or not spec.get('identity'):
            raise ResearchError(f'{role}: fields and identity are required')
        if not set(spec['identity']) <= set(spec['fields']):
            raise ResearchError(f'{role}: identity must refer to mapped field keys')
        if 'allow_distinct_artifact_files' in spec and (role != 'artifacts' or not isinstance(spec['allow_distinct_artifact_files'], bool)):
            raise ResearchError('allow_distinct_artifact_files is only a boolean artifact policy')
        guards = spec.get('creation_guard_keys', [])
        if guards and (not isinstance(guards, list) or not set(guards) <= set(spec['fields']) or
                       any(spec['fields'][key]['type'] != 'text' for key in guards)):
            raise ResearchError('creation_guard_keys must identify mapped text fields')
        if any(spec['fields'][k]['type'] != 'text' for k in spec['identity']):
            raise ResearchError('v1 identity fields must be explicitly mapped text fields')
        field_ids = [f.get('field_id') for f in spec['fields'].values()]
        if any(not x for x in field_ids) or len(set(field_ids)) != len(field_ids):
            raise ResearchError(f'{role}: field_ids must be nonempty and unique')
        if 'allow_create' in spec and not isinstance(spec['allow_create'], bool):
            raise ResearchError('allow_create must be a JSON boolean')
        for field in spec['fields'].values():
            for option in ('accept_upstream', 'prefer_upstream', 'allow_new_options', 'bootstrap_empty', 'allow_clear', 'allow_inference', 'identity_url', 'identity_url_first'):
                if option in field and not isinstance(field[option], bool):
                    raise ResearchError(option + ' must be a JSON boolean')
            if field.get('prefer_upstream') and not field.get('accept_upstream'):
                raise ResearchError('prefer_upstream requires accept_upstream')
            if field.get('allow_new_options') and not (field['type'] == 'select' and field.get('accept_upstream') and field.get('policy') == 'ai'):
                raise ResearchError('allow_new_options requires an upstream-managed select field')
            aliases = field.get('value_aliases', {})
            if not isinstance(aliases, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in aliases.items()):
                raise ResearchError('value_aliases must map strings to strings')
            if field.get('policy', 'unassigned') not in ('manual', 'ai', 'derived', 'readonly', 'unassigned'):
                raise ResearchError('unknown field policy')
        source = spec.get('input')
        if source and 'latest_snapshot' in source and not isinstance(source['latest_snapshot'], bool):
            raise ResearchError('latest_snapshot must be a JSON boolean')
        if source and source.get('kind', 'local') == 'local':
            source['directory'] = str((path.parent / source['directory']).resolve())
    cfg['_state'] = str(state)
    cfg['_hash'] = digest({k: v for k, v in cfg.items() if not k.startswith('_')})
    cfg['_path'] = str(path)
    if cfg.get('backend', {}).get('kind') == 'file':
        target = (path.parent / cfg['backend']['path']).resolve()
        if target.is_relative_to(checkout):
            raise ResearchError('file backend data must be outside the checkout')
        cfg['backend']['path'] = str(target)
    settings = cfg.get('agent', {})
    if settings.get('command') or settings.get('enabled'):
        raise ResearchError('AI generation and research queue were removed; use Grokbot and validate')
    validation = cfg.get('validation', {})
    if validation.get('baseline_state_dir'):
        validation['baseline_state_dir'] = str((path.parent / validation['baseline_state_dir']).resolve())
    scores = cfg.get('scores', {})
    if scores.get('enabled'):
        if set(cfg['roles']) != {'models'}:
            raise ResearchError('score maintenance must use a separate models-only configuration')
        for key in ('codex_state_dir', 'reference_file', 'sync_state_dir'):
            if scores.get(key):
                scores[key] = str((path.parent / scores[key]).resolve())
                if Path(scores[key]).is_relative_to(checkout):
                    raise ResearchError('score credentials and calibration must stay outside checkout')
        if not scores.get('model') or not scores.get('codex_state_dir'):
            raise ResearchError('score model and private Codex state are required')
        budget = scores.get('max_calls_per_day')
        if budget is not None and (isinstance(budget, bool) or not isinstance(budget, int) or budget < 1):
            raise ResearchError('invalid daily score model budget')
        threshold = scores.get('quota_stop_percent', 90)
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 < threshold <= 100:
            raise ResearchError('invalid score quota threshold')
    return cfg
