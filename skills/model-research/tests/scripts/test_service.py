from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

from support import Workspace, case
from common import ResearchError, read_json, write_json
from ingest import latest_snapshot
import service


class ServiceTests(Workspace):
    def install(self):
        self.config(lambda c: c.update(allow_writes=False))
        self.runtime = self.root / 'service'
        return service.install(self.runtime, self.config_path)

    @case(target='service.install', tags=('deployment', 'policy'))
    def test_install_rejects_enabled_online_writes(self):
        with self.assertRaisesRegex(ResearchError, 'allow_writes=false'):
            service.install(self.root / 'service', self.config_path)

    @case('integration', 'service.install -> release.research', ('deployment',))
    def test_frozen_release_runs_without_modifying_remote(self):
        installed = self.install()
        report = service.tick(self.runtime, '2026-11-13')
        self.assertEqual(report['status'], 'waiting_research')
        self.assertTrue(Path(report['research_request']).is_file())
        self.assertEqual(report['result']['operations'], 2)
        self.assertEqual(self.remote()['tables']['channels']['records'], [])
        self.assertTrue((Path(installed['release']) / 'skills/model-research/scripts/research.py').is_file())
        self.assertEqual(len([p for p in (self.root/'state/dossiers').glob('*.md') if p.name != 'README.md']), 2)

    @case('integration', 'service CSV-only release', ('csv', 'deployment'))
    def test_explicit_csv_workflow_does_not_report_missing_research_runtime(self):
        self.config(lambda cfg: cfg.update(agent={'enabled': False}))
        self.install()
        report = service.tick(self.runtime, '2026-11-13')
        self.assertEqual(report['research_runtime'], 'not_required')
        self.assertNotIn('research_request', report)
        self.assertEqual(report['status'], 'planned')

    @case(target='service.tick', tags=('deployment', 'policy'))
    def test_later_config_change_cannot_enable_service_writes(self):
        self.install()
        config = read_json(self.config_path)
        config['allow_writes'] = True
        write_json(self.config_path, config)
        with self.assertRaisesRegex(ResearchError, 'write-enabled'):
            service.tick(self.runtime, '2026-11-13')

    @case('integration', 'service.start -> service.stop', ('deployment', 'lifecycle'))
    def test_daemon_start_status_duplicate_start_and_stop(self):
        self.install()
        self.addCleanup(service.stop, self.runtime)
        result = service.start(self.runtime)
        self.assertEqual(result['status'], 'running')
        self.assertEqual(service.start(self.runtime)['process']['pid'], result['process']['pid'])
        self.assertEqual(service.stop(self.runtime)['status'], 'stopped')
        self.assertEqual(service.status(self.runtime)['status'], 'stopped')

    @case(target='service.next_due', tags=('schedule',))
    def test_schedule_uses_shanghai_and_defers_after_retry_window(self):
        settings = {'at': '15:00', 'retry_until': '18:00', 'retry_minutes': 30}
        before = datetime.fromisoformat('2026-11-14T06:00:00+00:00')
        self.assertEqual(service.next_due(settings, clock=before).isoformat(), '2026-11-14T15:00:00+08:00')
        after = datetime.fromisoformat('2026-11-14T10:00:00+00:00')
        self.assertEqual(service.next_due(settings, clock=after).isoformat(), '2026-11-15T15:00:00+08:00')

    @case(target='service.next_due', tags=('schedule',))
    def test_waiting_input_retry_is_bounded_by_window(self):
        settings = {'at': '15:00', 'retry_until': '18:00', 'retry_minutes': 30}
        previous = {'business_date': '2026-11-14', 'finished_at': '2026-11-14T17:45:00+08:00'}
        clock = datetime.fromisoformat('2026-11-14T17:46:00+08:00')
        self.assertEqual(service.next_due(settings, previous, clock).isoformat(), '2026-11-15T15:00:00+08:00')

    @case(target='service.next_due', tags=('schedule',))
    def test_manual_preflight_does_not_delay_the_first_scheduled_run(self):
        settings = {'at': '15:00', 'retry_until': '18:00', 'retry_minutes': 30}
        previous = {'business_date': '2026-11-14', 'finished_at': '2026-11-14T14:59:00+08:00'}
        clock = datetime.fromisoformat('2026-11-14T15:00:00+08:00')
        self.assertEqual(service.next_due(settings, previous, clock).isoformat(), '2026-11-14T15:00:00+08:00')

    @case(target='service.process', tags=('lifecycle',))
    def test_stale_pid_does_not_identify_an_unrelated_process(self):
        self.install()
        write_json(self.runtime/'process.json', {'pid': __import__('os').getpid(), 'start_ticks': 'incorrect'})
        self.assertIsNone(service.process(self.runtime))

    @case(target='ingest.latest_snapshot', tags=('snapshot',))
    def test_channel_snapshot_date_is_independent_of_daily_date(self):
        entries = [{'name': 'channels_2026-11-12.csv'}, {'name': 'channels_2026-11-13.csv'}, {'name': 'channels_2026-11-15.csv'}]
        self.assertEqual(latest_snapshot(entries, '2026-11-14'), [entries[1]])

    @case(target='ingest.latest_snapshot', tags=('snapshot', 'identity'))
    def test_same_date_snapshot_duplicates_are_not_silently_chosen(self):
        entries = [{'name': 'channels_2026-11-13.csv', 'token': 'a'}, {'name': 'channels_2026-11-13.csv', 'token': 'b'}]
        self.assertEqual(len(latest_snapshot(entries, '2026-11-14')), 2)

    @case('integration', 'service CLI', ('deployment',))
    def test_manage_command_can_query_installed_release(self):
        self.install()
        result = subprocess.run([str(self.runtime/'manage'), 'status'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'stopped')

    @case('e2e', 'service apply -> research.run -> file backend readback', ('deployment', 'writeback'))
    def test_explicit_apply_deployment_writes_and_repeat_has_no_duplicate_rows(self):
        runtime=self.root/'service'
        service.install(runtime,self.config_path,mode='apply')
        first=service.tick(runtime,'2026-11-13')
        self.assertEqual(first['result']['counts'],{'verified':2})
        self.assertEqual(len(self.remote()['tables']['channels']['records']),2)
        second=service.tick(runtime,'2026-11-13')
        self.assertEqual(second['result']['results'],[])

    @case(target='service.install', tags=('deployment','policy'))
    def test_apply_mode_requires_matching_write_permission(self):
        self.config(lambda c:c.update(allow_writes=False))
        with self.assertRaisesRegex(ResearchError,'allow_writes=true'):
            service.install(self.root/'service',self.config_path,mode='apply')

    @case(target='service.next_due',tags=('schedule','queue'))
    def test_active_backlog_continues_quickly_but_idle_returns_to_regular_polling(self):
        settings={'at':'15:00','retry_until':'18:00','retry_minutes':30,'continue_after_minutes':1}
        previous={'business_date':'2026-11-14','finished_at':'2026-11-14T15:05:00+08:00',
                  'result':{'research':{'processed':3,'remaining':100}}}
        clock=datetime.fromisoformat('2026-11-14T15:05:10+08:00')
        self.assertEqual(service.next_due(settings,previous,clock).isoformat(),'2026-11-14T15:06:00+08:00')
        previous['result']['research']['processed']=0
        self.assertEqual(service.next_due(settings,previous,clock).isoformat(),'2026-11-14T15:35:00+08:00')

    @case(target='service.next_due',tags=('schedule','readiness'))
    def test_stability_observation_resumes_without_waiting_half_an_hour(self):
        settings={'at':'15:00','retry_until':'18:00','retry_minutes':30,'continue_after_minutes':1}
        previous={'business_date':'2026-11-14','finished_at':'2026-11-14T15:05:00+08:00',
                  'result':{'readiness':'observing'}}
        clock=datetime.fromisoformat('2026-11-14T15:05:10+08:00')
        self.assertEqual(service.next_due(settings,previous,clock).isoformat(),'2026-11-14T15:06:00+08:00')
