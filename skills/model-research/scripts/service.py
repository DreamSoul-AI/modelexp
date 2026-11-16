#!/usr/bin/env python3
"""Install fixed releases and supervise CSV, validation and score maintenance."""
import argparse
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time as runtime_time
from zoneinfo import ZoneInfo

from common import ResearchError, atomic_write, digest, load_config, now, read_json, run_process, write_json

TZ = ZoneInfo('Asia/Shanghai')
SKILL = Path(__file__).resolve().parents[1]


@contextmanager
def exclusive(path):
    with Path(path).open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ResearchError('another service process owns this lock') from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def install(root, config, at='15:00', retry_minutes=30, retry_until='18:00', mode='plan', continue_after_minutes=None, start_date=None):
    root = Path(root).resolve()
    cfg = load_config(config)
    if mode == 'plan' and cfg.get('allow_writes', False):
        raise ResearchError('this trial deployment requires allow_writes=false')
    if mode == 'validate' and cfg.get('allow_writes', False):
        raise ResearchError('validation deployment requires allow_writes=false')
    if mode not in ('plan', 'apply', 'validate', 'scores') or mode == 'apply' and not cfg.get('allow_writes', False):
        raise ResearchError('apply deployment requires allow_writes=true')
    if start_date is not None:
        start_date = date.fromisoformat(start_date).isoformat()
    time.fromisoformat(at)
    time.fromisoformat(retry_until)
    if at >= retry_until or not 1 <= retry_minutes <= 180:
        raise ResearchError('invalid schedule window or retry interval')
    if continue_after_minutes is not None and not 1 <= continue_after_minutes <= 60:
        raise ResearchError('continue_after_minutes must be between 1 and 60')
    if root.is_relative_to(SKILL.parents[1]):
        raise ResearchError('deployment must be outside the source checkout')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if process(root):
        raise ResearchError('stop this service before replacing its release')
    files = sorted(p for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    signature = digest([[str(p.relative_to(SKILL)), hashlib.sha256(p.read_bytes()).hexdigest()] for p in files])
    release = root / 'releases' / signature[:20]
    target = release / 'skills' / 'model-research'
    if not target.exists():
        target.mkdir(parents=True)
        for source in files:
            destination = target / source.relative_to(SKILL)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    current = root / 'current'
    pending = root / '.current-new'
    pending.unlink(missing_ok=True)
    pending.symlink_to(release.relative_to(root), target_is_directory=True)
    os.replace(pending, current)
    config = Path(config).resolve()
    settings = {'schema_version': 1, 'release': str(release), 'source_sha256': signature,
                'config': str(config), 'python': sys.executable, 'mode': mode,
                'timezone': 'Asia/Shanghai', 'at': at, 'retry_minutes': retry_minutes,
                'retry_until': retry_until, 'installed_at': now(),
                'continue_after_minutes': continue_after_minutes, 'start_date': start_date,
                'lifecycle': 'current cloud environment only; no host restart integration'}
    write_json(root / 'deployment.json', settings)
    command = [sys.executable, str(current / 'skills/model-research/scripts/service.py'), '--root', str(root)]
    atomic_write(root / 'manage', '#!/bin/sh\nexec ' + shlex.join(command) + ' "$@"\n')
    (root / 'manage').chmod(0o700)
    return {'status': 'installed', **settings, 'management_command': str(root / 'manage')}


def process(root):
    path = Path(root) / 'process.json'
    if not path.exists():
        return None
    info = read_json(path)
    try:
        # Start time guards against a PID being reused by another process.
        stat = Path(f"/proc/{info['pid']}/stat").read_text().rsplit(')', 1)[1].split()
        if stat[0] == 'Z' or stat[19] != info['start_ticks']:
            return None
        command = Path(f"/proc/{info['pid']}/cmdline").read_bytes().split(b'\0')
        if str(Path(root).resolve()).encode() not in command or b'daemon' not in command:
            return None
        return info
    except (FileNotFoundError, ProcessLookupError):
        return None


def next_due(settings, previous=None, clock=None):
    clock = (clock or datetime.now(TZ)).astimezone(TZ)
    first_day = date.fromisoformat(settings['start_date']) if settings.get('start_date') else clock.date()
    opening = datetime.combine(max(clock.date(), first_day), time.fromisoformat(settings['at']), TZ)
    closing = datetime.combine(clock.date(), time.fromisoformat(settings['retry_until']), TZ)
    if clock < opening:
        return opening
    if clock >= closing:
        return opening + timedelta(days=1)
    if previous and previous.get('business_date') == clock.date().isoformat():
        finished = datetime.fromisoformat(previous['finished_at'])
        if finished < opening:
            return opening
        interval = settings['retry_minutes']
        result = previous.get('result', {})
        if settings.get('continue_after_minutes') and (result.get('readiness') == 'observing' or
                settings.get('mode') == 'scores' and result.get('processed', 0) > 0 and result.get('eligible', 0) > result.get('processed', 0)):
            interval = settings['continue_after_minutes']
        due = finished + timedelta(minutes=interval)
        return due if due < closing else opening + timedelta(days=1)
    return clock


def tick(root, business_date=None):
    root = Path(root).resolve()
    settings = read_json(root / 'deployment.json')
    cfg = load_config(settings['config'])
    if settings['mode'] == 'plan' and cfg.get('allow_writes', False):
        raise ResearchError('trial service refuses a write-enabled configuration')
    if settings['mode'] == 'validate' and cfg.get('allow_writes', False):
        raise ResearchError('validation service refuses a write-enabled configuration')
    if settings['mode'] not in ('plan', 'apply', 'validate', 'scores') or settings['mode'] == 'apply' and not cfg.get('allow_writes', False):
        raise ResearchError('deployment mode and write configuration disagree')
    business_date = business_date or datetime.now(TZ).date().isoformat()
    report = {'started_at': now(), 'business_date': business_date, 'mode': settings['mode'],
              'source_sha256': settings['source_sha256'], 'model_calls': 0}
    with exclusive(root / 'tick.lock'):
        script = Path(settings['release']) / 'skills/model-research/scripts/research.py'
        command = [settings['python'], str(script), settings['mode'] if settings['mode'] in ('validate', 'scores') else 'run',
                   '--config', settings['config'], '--date', business_date]
        if settings['mode'] != 'validate':
            command += ['--mode', ('apply' if cfg.get('allow_writes') else 'plan') if settings['mode'] == 'scores' else settings['mode']]
        try:
            timeout = max(240, cfg.get('worker_timeout_seconds', 600) + 60)
            result = run_process(command, timeout=timeout)
            report['exit_code'] = result.returncode
            if result.returncode in (0, 3):
                report['result'] = json.loads(result.stdout)
                report['model_calls'] = report['result'].get('model_calls', 0)
                report['status'] = report['result']['status']
            else:
                report.update(status='error', reason='worker failed; inspect private worker result')
            private = root / 'worker-results' / (now().replace(':', '-') + '-' + str(os.getpid()) + '.json')
            write_json(private, {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
            report['worker_result'] = str(private)
        except subprocess.TimeoutExpired:
            report.update(status='error', reason='worker exceeded its configured deadline')
        report['finished_at'] = now()
        write_json(root / 'last-run.json', report)
        write_json(root / 'runs' / (digest(report)[:24] + '.json'), report)
    return report


def status(root):
    root = Path(root).resolve()
    settings = read_json(root / 'deployment.json')
    cfg = load_config(settings['config'])
    previous = read_json(root / 'last-run.json') if (root / 'last-run.json').exists() else None
    live = process(root)
    return {'status': 'running' if live else 'stopped', 'process': live, 'mode': settings['mode'],
            'allow_writes': cfg.get('allow_writes', False), 'next_run': next_due(settings, previous).isoformat(),
            'model_calls': settings['mode'] == 'scores',
            'deployment': settings, 'last_run': previous}


def daemon(root):
    root = Path(root).resolve()
    settings = read_json(root / 'deployment.json')
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    with exclusive(root / 'daemon.lock'):
        stat = Path(f'/proc/{os.getpid()}/stat').read_text().rsplit(')', 1)[1].split()
        info = {'pid': os.getpid(), 'start_ticks': stat[19], 'started_at': now()}
        write_json(root / 'process.json', info)
        while not stop.is_set():
            previous = read_json(root / 'last-run.json') if (root / 'last-run.json').exists() else None
            due = next_due(settings, previous)
            write_json(root / 'heartbeat.json', {'observed_at': now(), 'next_run': due.isoformat(), 'pid': os.getpid()})
            if datetime.now(TZ) >= due:
                try:
                    tick(root)
                except (ResearchError, OSError, ValueError) as exc:
                    report = {'status': 'error', 'business_date': datetime.now(TZ).date().isoformat(),
                              'finished_at': now(), 'reason': str(exc)}
                    write_json(root / 'last-run.json', report)
            stop.wait(30)
        write_json(root / 'stopped.json', {'stopped_at': now(), 'pid': os.getpid()})


def start(root):
    root = Path(root).resolve()
    if process(root):
        return status(root)
    settings = read_json(root / 'deployment.json')
    cfg = load_config(settings['config'])
    if settings['mode'] == 'plan' and cfg.get('allow_writes', False):
        raise ResearchError('trial service refuses a write-enabled configuration')
    if settings['mode'] == 'validate' and cfg.get('allow_writes', False):
        raise ResearchError('validation service refuses a write-enabled configuration')
    if settings['mode'] == 'apply' and not cfg.get('allow_writes', False):
        raise ResearchError('apply deployment requires allow_writes=true')
    script = Path(settings['release']) / 'skills/model-research/scripts/service.py'
    with (root / 'service.log').open('a') as log:
        child = subprocess.Popen([settings['python'], str(script), '--root', str(root), 'daemon'],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, cwd=root)
    for _ in range(30):
        if process(root):
            return status(root)
        if child.poll() is not None:
            raise ResearchError('service exited during startup; inspect private service.log')
        runtime_time.sleep(0.1)
    raise ResearchError('service startup has not been observed')


def stop(root):
    info = process(root)
    if not info:
        return {'status': 'stopped'}
    # Only this verified daemon's own session is stopped, including its read-only worker.
    if os.getpgid(info['pid']) != info['pid']:
        raise ResearchError('service is not its expected process group leader')
    os.killpg(info['pid'], signal.SIGTERM)
    for _ in range(100):
        if not process(root):
            return {'status': 'stopped'}
        runtime_time.sleep(0.1)
    raise ResearchError('service has not stopped within ten seconds')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    install_parser = commands.add_parser('install')
    install_parser.add_argument('--config', required=True)
    install_parser.add_argument('--at', default='15:00')
    install_parser.add_argument('--retry-until', default='18:00')
    install_parser.add_argument('--retry-minutes', type=int, default=30)
    install_parser.add_argument('--mode', choices=('plan', 'apply', 'validate', 'scores'), default='plan')
    install_parser.add_argument('--continue-after-minutes', type=int)
    install_parser.add_argument('--start-date', help='First automatic business date in Asia/Shanghai; explicit ticks remain available')
    for command in ('start', 'stop', 'status', 'daemon'):
        commands.add_parser(command)
    tick_parser = commands.add_parser('tick')
    tick_parser.add_argument('--date')
    args = parser.parse_args()
    if args.command == 'install':
        return install(args.root, args.config, args.at, args.retry_minutes, args.retry_until, args.mode, args.continue_after_minutes, args.start_date)
    if args.command == 'tick':
        return tick(args.root, args.date)
    return globals()[args.command](args.root)


if __name__ == '__main__':
    try:
        result = main()
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ResearchError, ValueError, OSError, KeyError) as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
