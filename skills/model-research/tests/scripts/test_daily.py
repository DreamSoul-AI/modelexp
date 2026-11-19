from copy import deepcopy
import hashlib
from unittest.mock import patch

from support import Workspace, case
from common import ResearchError, read_json, write_json
import daily


class DailyTests(Workspace):
    def configure_tables(self):
        cfg = read_json(self.config_path)
        for role in ('models', 'artifacts'):
            spec = deepcopy(cfg['roles']['channels'])
            spec['input']['filename'] = role + '_{date}.csv'
            cfg['roles'][role] = spec
            (self.root / ('incoming/' + role + '_2026-11-13.csv')).write_bytes(
                (self.root / 'incoming/channels_2026-11-13.csv').read_bytes())
        cfg['backend']['batch_size'] = 200
        for spec in cfg['roles'].values():
            for rule in spec['fields'].values():
                rule.update(accept_upstream=True, prefer_upstream=True)
        write_json(self.config_path, cfg)
        remote = self.remote()
        for role in ('models', 'artifacts'):
            remote['tables'][role] = deepcopy(remote['tables']['channels'])
        write_json(self.root / 'remote.json', remote)
        self.open()

    @case('integration', 'daily -> missing required table -> independent writes and repeat', ('csv', 'independence'))
    def test_missing_table_does_not_block_available_tables_or_duplicate_on_late_arrival(self):
        self.configure_tables()
        path = self.root / 'incoming/channels_2026-11-13.csv'
        saved = path.read_bytes();path.unlink()
        result = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['roles']['channels']['status'], 'waiting_input')
        self.assertEqual(result['roles']['models']['status'], 'completed')

        self.assertEqual(result['roles']['artifacts']['status'], 'completed')
        self.assertEqual(result['counts'], {'verified': 4})
        path.write_bytes(saved)
        late = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(late['counts'], {'verified': 2})
        self.assertEqual(late['status'], 'completed')
        repeated = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(repeated['results'], [])
        self.assertTrue(all(len(t['records']) == 2 for t in self.remote()['tables'].values()))

    @case('integration', 'daily -> only optional input absent', ('csv', 'readiness'))
    def test_only_optional_missing_input_is_not_a_required_delivery_wait(self):
        self.config(lambda cfg: cfg['roles']['channels']['input'].update(required=False))
        (self.root / 'incoming/channels_2026-11-13.csv').unlink()
        result = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['roles']['channels']['status'], 'skipped')

    @case('integration', 'daily -> one invalid CSV -> other tables continue', ('csv', 'independence'))
    def test_duplicate_identity_in_one_csv_does_not_suppress_other_tables(self):
        self.configure_tables()
        path = self.root / 'incoming/models_2026-11-13.csv'
        text = path.read_text();path.write_text(text + text.splitlines(keepends=True)[1])
        result = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(result['roles']['models']['readiness'], 'invalid')
        self.assertEqual(result['roles']['channels']['status'], 'completed')
        self.assertEqual(result['roles']['artifacts']['status'], 'completed')
        self.assertEqual(self.remote()['tables']['models']['records'], [])
        self.assertEqual(result['counts'], {'verified': 4})

    @case('integration', 'daily -> independent source stability', ('csv', 'readiness'))
    def test_later_delivery_does_not_reset_existing_tables_stability_clock(self):
        self.configure_tables()
        self.config(lambda cfg: cfg.update(allow_unconfirmed_input=False,
                    input_readiness={'strategy': 'stable_observations', 'min_interval_seconds': 60}))
        path = self.root / 'incoming/artifacts_2026-11-13.csv'
        saved = path.read_bytes();path.unlink()
        with patch('ingest.now', return_value='2026-11-13T12:00:00+08:00'):
            first = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(first['results'], [])
        path.write_bytes(saved)
        with patch('ingest.now', return_value='2026-11-13T12:01:01+08:00'):
            second = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(second['roles']['models']['readiness'], 'observed_stable')
        self.assertEqual(second['roles']['artifacts']['status'], 'waiting_input')
        self.assertEqual(second['counts'], {'verified': 4})
        with patch('ingest.now', return_value='2026-11-13T12:02:02+08:00'):
            third = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(third['counts'], {'verified': 2})

    @case('integration', 'daily -> completed model receipt -> later backend failure', ('csv', 'scores'))
    def test_model_completion_is_published_before_later_table_failure(self):
        self.configure_tables()
        snapshot = self.backend.snapshot
        def fail_later(role, spec):
            if role == 'artifacts':
                receipt = read_json(self.state.root / 'daily/models-latest.json')
                self.assertEqual(receipt['status'], 'completed')
                raise ResearchError('table unavailable')
            return snapshot(role, spec)
        with patch.object(self.backend, 'snapshot', side_effect=fail_later):
            result = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(result['roles']['models']['status'], 'completed')
        self.assertEqual(result['roles']['artifacts']['status'], 'partial')

    @case('integration', 'daily validate -> invalid table -> compare other tables', ('validation', 'independence'))
    def test_validation_keeps_other_comparisons_when_one_csv_is_invalid(self):
        self.configure_tables()
        daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        path = self.root / 'incoming/models_2026-11-13.csv'
        path.write_text('bad_header\nbad_row\n')
        self.config(lambda cfg: cfg.update(allow_writes=False))
        before = self.remote()
        result = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'validate')
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['roles']['models']['readiness'], 'invalid')
        self.assertEqual(result['tables']['channels']['matched_rows'], 2)
        self.assertEqual(result['tables']['artifacts']['matched_rows'], 2)
        self.assertEqual(result['remote_writes'], 0)
        self.assertEqual(self.remote(), before)
        self.assertEqual(read_json(self.state.root / 'validation/latest.json')['tables'], result['tables'])

    @case('integration', 'daily -> missing optional CSV', ('csv', 'readiness'))
    def test_missing_optional_table_is_skipped_without_hiding_required_missing_input(self):
        self.configure_tables()
        self.config(lambda cfg: cfg['roles']['artifacts']['input'].update(required=False))
        (self.root / 'incoming/artifacts_2026-11-13.csv').unlink()
        result = daily.execute(self.cfg, self.state, self.backend, '2026-11-13', 'apply')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['roles']['artifacts']['status'], 'skipped')
        self.assertEqual(result['roles']['models']['status'], 'completed')

    @case('integration', 'daily -> Codex handoff -> zero-row input', ('delivery', 'readiness'))
    def test_handoff_blocks_unowned_input_and_accepts_verified_empty_day(self):
        day = '2026-11-13'
        self.config(lambda cfg: cfg.update(input_handoff={'start_date': day, 'directory': 'handoff'}))
        before = self.remote()
        result = daily.execute(self.cfg, self.state, self.backend, day, 'apply')
        self.assertEqual(result['roles']['channels']['status'], 'waiting_input')
        self.assertEqual(result['issues'][0]['reason'], 'waiting_for_codex_delivery')
        self.assertEqual(self.remote(), before)
        path = self.root / 'incoming' / ('channels_' + day + '.csv')
        path.write_bytes(path.read_bytes().splitlines(keepends=True)[0])
        marker = self.root / 'handoff' / (day + '.json')
        manifest = {'business_date': day, 'complete': True,
                    'files': {'channels': {'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                           'allow_empty': True}}}
        write_json(marker, manifest)
        result = daily.execute(self.cfg, self.state, self.backend, day, 'apply')
        self.assertEqual(result['roles']['channels']['status'], 'completed')
        self.assertEqual(result['readiness'], 'producer_confirmed')
        self.assertEqual(result['operations'], 0)
        self.assertEqual(self.remote(), before)
        path.write_bytes(path.read_bytes() + b'changed after readback')
        result = daily.execute(self.cfg, self.state, self.backend, day, 'apply')
        self.assertEqual(result['roles']['channels']['readiness'], 'invalid')
        self.assertEqual(self.remote(), before)
