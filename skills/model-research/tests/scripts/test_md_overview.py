from copy import deepcopy
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from support import Workspace, case
from common import ResearchError
from lark_adapter import UncertainWrite
import md_overview
import service


def file(token, name):
    return {'type': 'file', 'token': token, 'name': name, 'url': 'https://example.org/file/' + token,
            'modified_time': '1794945600'}


class Drive:
    def __init__(self):
        self.folders = {'root': [{'type': 'folder', 'token': 'old', 'name': 'existing', 'url': 'https://example.org/old'},
                                 {'type': 'folder', 'token': 'day', 'name': '2026-11-18', 'url': 'https://example.org/day'}],
                        'old': [file('a', 'models_a.md'), file('idx', 'README.md')],
                        'day': [file('b', 'benchmarks_b.md'), file('c', 'quant_c.md')]}
        self.contents, self.failures, self.writes, self.lost_ack = {}, set(), [], False

    def list_files(self, folder):
        if folder in self.failures: raise ResearchError('folder unavailable')
        return deepcopy(self.folders[folder])

    def markdown_fetch(self, token):
        return self.contents[token]

    def markdown_write(self, folder, path, token=None):
        token = token or 'overview'
        self.writes.append(token)
        self.contents[token] = Path(path).read_text()
        if not any(f['token'] == token for f in self.folders[folder]):
            self.folders[folder].append(file(token, 'README.md'))
        if self.lost_ack:
            self.lost_ack = False
            raise UncertainWrite('lost acknowledgement')
        return {'file_token': token}


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.cfg = {'_state': self.temp.name, 'allow_writes': True,
                    'md_overview': {'enabled': True, 'folder_token': 'root'}}
        self.drive = Drive()

    def update(self, mode='apply'):
        return md_overview.execute(self.cfg, self.drive, '2026-11-18', mode)

    @case('integration', 'overview scan -> create -> readback -> repeat', ('overview', 'idempotence'))
    def test_counts_exclude_indexes_and_repeat_does_not_create_or_overwrite(self):
        first = self.update();second = self.update()
        self.assertEqual(first['body_files'], 3)
        self.assertEqual(first['remote_writes'], 1)
        self.assertEqual(second['action'], 'unchanged')
        self.assertEqual(self.drive.writes, ['overview'])
        self.assertEqual(len(list(Path(self.temp.name).glob('md-overview/candidates/*/README.md'))), 1)
        content = self.drive.contents['overview']
        self.assertIn('| 正文 MD 总数 | 3 |', content)
        self.assertIn('| 模型文档数 | 1 |', content)
        self.assertIn('https://example.org/file/b', content)
        self.assertNotIn('最早业务日期', content)

    @case('integration', 'overview -> new file -> overwrite same token', ('overview', 'writeback'))
    def test_new_file_updates_the_same_overview(self):
        self.update();self.drive.folders['day'].append(file('d', 'models_d.md'))
        result = self.update()
        self.assertEqual(result['body_files'], 4)
        self.assertEqual(result['action'], 'updated')
        self.assertEqual(self.drive.writes, ['overview', 'overview'])
        self.assertEqual(sum(f['name'] == 'README.md' for f in self.drive.folders['root']), 1)

    @case('integration', 'overview -> lost create acknowledgement -> reconcile', ('overview', 'recovery'))
    def test_lost_ack_is_reconciled_without_creating_a_duplicate(self):
        self.drive.lost_ack = True
        self.assertEqual(self.update()['reason'], 'overview_submission_unverified')
        result = self.update()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.drive.writes, ['overview'])

    @case('integration', 'overview -> human edit -> protected candidate', ('overview', 'human'))
    def test_manual_changes_are_preserved(self):
        self.update();self.drive.contents['overview'] += '\nHuman note\n'
        result = self.update()
        self.assertEqual(result['reason'], 'overview_changed_or_not_owned')
        self.assertTrue(self.drive.contents['overview'].endswith('Human note\n'))
        self.assertEqual(len(self.drive.writes), 1)

    @case('integration', 'overview -> incomplete scan -> retain last complete inventory', ('overview', 'readiness'))
    def test_incomplete_scan_labels_old_totals_and_keeps_prior_index(self):
        self.update();self.drive.failures.add('old')
        result = self.update();content = self.drive.contents['overview']
        self.assertEqual(result['status'], 'partial')
        self.assertIn('上次完整盘点正文数 | 3', content)
        self.assertIn('models_a.md', content)
        self.assertIn('部分完成', content)

    @case('integration', 'overview -> readonly render', ('overview', 'readonly'))
    def test_plan_creates_a_local_candidate_without_remote_writes(self):
        self.cfg['allow_writes'] = False
        result = self.update('plan')
        self.assertTrue(Path(result['candidate_path']).exists())
        self.assertEqual(self.drive.writes, [])

    @case(target='md_overview.scan', tags=('overview', 'coverage'))
    def test_inventory_does_not_truncate_large_directories_or_double_count_repeated_entries(self):
        self.drive.folders['day'] = [file(str(i), 'models_'+str(i)+'.md') for i in range(700)]
        self.drive.folders['day'].append(deepcopy(self.drive.folders['day'][0]))
        snapshot = md_overview.scan(self.drive, 'root')
        self.assertTrue(snapshot['complete'])
        self.assertEqual(len(snapshot['records']), 701)

    @case('integration', 'overview -> unknown pending create -> pause', ('overview', 'recovery'))
    def test_unknown_create_is_not_blindly_retried_when_file_is_not_visible(self):
        self.drive.lost_ack = True;self.update()
        self.drive.folders['root'] = [e for e in self.drive.folders['root'] if e['token'] != 'overview']
        self.assertEqual(self.update()['reason'], 'unknown_submission_requires_reconciliation')
        self.assertEqual(len(self.drive.writes), 1)


class OverviewHookTests(Workspace):
    @case('integration', 'service validate -> overview disabled for readonly task', ('overview', 'readonly'))
    def test_readonly_validation_never_runs_the_write_hook(self):
        self.config(lambda cfg: cfg.update(allow_writes=False, md_overview={'enabled': True, 'folder_token': 'root'}))
        runtime = self.root / 'service';service.install(runtime, self.config_path, mode='validate')
        with patch('service.run_process', return_value=subprocess.CompletedProcess([], 0, '{"status":"completed"}', '')) as run:
            report = service.tick(runtime, '2026-11-18')
        self.assertEqual(run.call_count, 1)
        self.assertNotIn('md_overview', report)

    def install(self):
        self.config(lambda cfg: cfg.update(md_overview={'enabled': True, 'folder_token': 'root'}))
        self.runtime = self.root / 'service'
        service.install(self.runtime, self.config_path, mode='apply')

    @case('integration', 'service -> waiting CSV -> overview update', ('overview', 'schedule'))
    def test_hook_runs_after_missing_csv_without_claiming_csv_completion(self):
        self.install()
        values = [{'status': 'waiting_input', 'readiness': 'observing'}, {'status': 'completed', 'body_files': 3}]
        with patch('service.run_process', side_effect=[subprocess.CompletedProcess([], 3 if i == 0 else 0, json.dumps(v), '') for i,v in enumerate(values)]) as run:
            report = service.tick(self.runtime, '2026-11-18')
        self.assertEqual(report['status'], 'waiting_input')
        self.assertEqual(report['md_overview']['status'], 'completed')
        self.assertIn('md-overview', run.call_args_list[1].args[0])

    @case('integration', 'service -> overview failure -> partial report', ('overview', 'schedule'))
    def test_failed_overview_is_visible_without_hiding_csv_result(self):
        self.install()
        with patch('service.run_process', side_effect=[subprocess.CompletedProcess([], 0, '{"status":"completed"}', ''),
                                                       subprocess.CompletedProcess([], 2, '', 'private failure')]):
            report = service.tick(self.runtime, '2026-11-18')
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['result']['status'], 'completed')
        self.assertEqual(report['md_overview']['reason'], 'overview_update_failed')
