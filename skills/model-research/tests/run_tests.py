#!/usr/bin/env python3
"""Stdlib categorical test runner: selectable cases and durable per-case results."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
import uuid

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'scripts'))


class CaseTimeout(TimeoutError):
    pass


class PersistentResult(unittest.TextTestResult):
    def __init__(self, *args, output, run_id, timeout, **kwargs):
        super().__init__(*args, **kwargs)
        self.output, self.run_id, self.timeout = output, run_id, timeout
        self.previous_handler = None

    def startTest(self, test):
        super().startTest(test)
        self.start = time.monotonic()
        self.started_at = datetime.now(timezone.utc).isoformat()
        if self.timeout:
            self.previous_handler = signal.signal(signal.SIGALRM, self.expired)
            signal.setitimer(signal.ITIMER_REAL, self.timeout)

    def expired(self, *_):
        raise CaseTimeout('per-case wall time limit exceeded')

    def stopTest(self, test):
        if self.timeout:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self.previous_handler)
        super().stopTest(test)

    def record(self, test, status, error=None):
        method = getattr(test, test._testMethodName, None)
        metadata = getattr(method, 'test_metadata', {})
        duration = (time.monotonic()-self.start)*1000
        event = {**metadata, 'run_id': self.run_id, 'test_id': test.id(), 'attempt': 1,
                 'status': status, 'verdict': 'pass' if status == 'passed' else ('fail' if status == 'failed' else None),
                 'category': 'pass' if status == 'passed' else ('fail' if status == 'failed' else None),
                 'result_detail': 'summary', 'environment_id': 'local_cpu', 'started_at': self.started_at,
                 'duration_ms': duration, 'cost': {'estimated_wall_time_ms': None, 'actual_wall_time_ms': duration},
                 'failure': error, 'artifacts': []}
        with (self.output/'events.jsonl').open('a') as stream:
            stream.write(json.dumps(event, ensure_ascii=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, 'passed')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, 'failed', ''.join(traceback.format_exception(*err)))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, 'timeout' if issubclass(err[0], CaseTimeout) else 'error', ''.join(traceback.format_exception(*err)))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, 'skipped', reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.record(test, 'xfail', ''.join(traceback.format_exception(*err)))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.record(test, 'xpass')


def flatten(suite):
    for entry in suite:
        if isinstance(entry, unittest.TestSuite):
            yield from flatten(entry)
        else:
            yield entry


def report(output):
    manifest = json.loads((output/'manifest.json').read_text())
    events = [json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()] if (output/'events.jsonl').exists() else []
    counts = dict(Counter(e['status'] for e in events))
    missing = sorted(set(manifest['selected']) - {e['test_id'] for e in events})
    text = '# 自动化测试运行报告\n\n' + f"- Run: {manifest['run_id']}\n- Results: {counts}\n- Missing results: {len(missing)}\n\n"
    for event in events:
        if event['status'] != 'passed':
            text += f"## {event['test_id']}\n\n{event['status']}\n\n```text\n{event['failure']}\n```\n\n"
    if missing:
        text += '## 未完成\n\n' + '\n'.join('- '+x for x in missing)+'\n'
    (output/'report.md').write_text(text)
    return counts, missing


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('level', 'type', 'priority', 'module', 'tag', 'case', 'cost-class', 'result-type'):
        p.add_argument('--'+key)
    p.add_argument('--timeout', type=float, default=30)
    p.add_argument('--output')
    p.add_argument('--report-only')
    p.add_argument('--resume-from')
    args = p.parse_args()
    if args.report_only:
        print(report(Path(args.report_only)))
        return 0
    discovered = list(flatten(unittest.defaultTestLoader.discover(str(ROOT/'scripts'), pattern='test_*.py')))
    old_passed = set()
    if args.resume_from:
        old = Path(args.resume_from)/'events.jsonl'
        old_passed = {x['test_id'] for x in map(json.loads, old.read_text().splitlines()) if x['status']=='passed'}
    selected, excluded = [], []
    for test in discovered:
        meta = getattr(getattr(test, test._testMethodName, None), 'test_metadata', {})
        include = all(not getattr(args, k) or meta.get(k) == getattr(args, k) for k in ('level', 'type', 'priority', 'cost_class', 'result_type'))
        include = include and (not args.module or args.module in test.id()) and (not args.case or args.case in test.id())
        include = include and (not args.tag or args.tag in meta.get('tags', [])) and test.id() not in old_passed
        (selected if include else excluded).append(test)
    if not selected:
        print('No tests selected; this is not a passing validation.', file=sys.stderr)
        return 2
    output = Path(args.output or tempfile.mkdtemp(prefix='model-research-tests-')).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output/'manifest.json').exists():
        p.error('output directory already has a run; use a fresh path')
    run_id = 'tests_'+uuid.uuid4().hex
    version = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
    sources = sorted(p for p in ROOT.parent.rglob('*') if p.is_file() and p.suffix in ('.py', '.md', '.json') and '__pycache__' not in p.parts)
    tree_hash = hashlib.sha256()
    for source in sources:
        tree_hash.update(str(source.relative_to(ROOT.parent)).encode() + b'\0' + source.read_bytes() + b'\0')
    manifest = {'source_tree_sha256': tree_hash.hexdigest(), 'run_id': run_id, 'command': sys.argv, 'python': sys.version, 'platform': platform.platform(),
                'git_head': version, 'selected': [t.id() for t in selected], 'excluded': [t.id() for t in excluded],
                'timeout_per_case_seconds': args.timeout, 'resource_scope': 'CPU, local temporary files, no cloud writes',
                'resume_from': args.resume_from, 'started_at': datetime.now(timezone.utc).isoformat()}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    runner = unittest.TextTestRunner(verbosity=2, resultclass=lambda *a,**kw: PersistentResult(*a,output=output,run_id=run_id,timeout=args.timeout,**kw))
    result = runner.run(unittest.TestSuite(selected))
    counts, missing = report(output)
    print(json.dumps({'output':str(output),'results':counts,'missing':missing},ensure_ascii=False))
    return 0 if result.wasSuccessful() and not missing and not result.skipped and not result.expectedFailures else 1


if __name__ == '__main__':
    raise SystemExit(main())
