from copy import deepcopy
from unittest.mock import patch

from support import Workspace, case
from common import ResearchError, read_json, write_json
from research import main
import service
import validation


class ValidationTests(Workspace):
    def check(self):
        self.config(lambda c: c.update(allow_writes=False))
        return validation.execute(self.cfg, self.state, self.batch(), self.backend)

    @case('integration', 'validation -> snapshot and compare -> reports', ('validation', 'readonly'))
    def test_matching_rows_pass_without_writes_or_baseline_changes(self):
        self.seed()
        remote = self.remote()
        baselines = list(map(tuple, self.state.db.execute('SELECT * FROM baselines')))
        with patch.object(self.backend, 'create', side_effect=AssertionError('no writes')), \
                patch.object(self.backend, 'update', side_effect=AssertionError('no writes')):
            result = self.check()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['tables']['channels']['matched_rows'], 2)
        self.assertFalse(result['model_calls'])
        self.assertFalse(result['factual_verification'])
        self.assertEqual(self.remote(), remote)
        self.assertEqual(list(map(tuple, self.state.db.execute('SELECT * FROM baselines'))), baselines)
        self.assertTrue(__import__('pathlib').Path(result['issues_csv']).exists())

    @case('integration', 'validation -> missing row and historical rows', ('validation', 'incremental'))
    def test_missing_current_row_is_reported_but_historical_rows_are_kept(self):
        self.seed()
        def change(table):
            extra = deepcopy(table['records'][0])
            extra['record_id'] = 'historical'
            extra['fields']['fld_url'] = 'https://example.org/old'
            table['records'][0] = extra
        self.edit_remote(change)
        result = self.check()
        self.assertEqual([i['reason'] for i in result['issues']], ['missing_remote_record'])
        self.assertEqual(result['tables']['channels']['historical_rows'], 1)
        self.assertEqual(len(self.remote()['tables']['channels']['records']), 2)

    @case('integration', 'validation -> identity ambiguity', ('validation', 'identity'))
    def test_duplicate_identity_is_reported_without_matching_by_name(self):
        self.seed()
        def duplicate(table):
            extra = deepcopy(table['records'][0]); extra['record_id'] = 'duplicate'
            table['records'].append(extra)
        self.edit_remote(duplicate)
        result = self.check()
        self.assertTrue(any(i['reason'] == 'duplicate_remote_identity' for i in result['issues']))
        self.assertEqual(result['tables']['channels']['matched_rows'], 1)

    @case('integration', 'validation -> CSV differences', ('validation', 'values'))
    def test_unsynced_csv_value_is_reported_with_expected_and_actual(self):
        self.seed()
        self.edit_csv(lambda rows: rows[0].update(备注='New upstream value'))
        result = self.check()
        mismatch = next(i for i in result['issues'] if i['reason'] == 'csv_remote_mismatch')
        self.assertEqual(mismatch['expected'], 'New upstream value')
        self.assertNotEqual(mismatch['actual'], mismatch['expected'])
        self.assertEqual(mismatch['source_row'], 2)

    @case('integration', 'validation -> human mirror baseline', ('validation', 'human'))
    def test_previously_preserved_human_change_is_not_reported_as_wrong(self):
        self.seed()
        self.edit_remote(lambda table: table['records'][0]['fields'].update(fld_note='Human correction'))
        import sync
        sync.apply(self.cfg, self.state, self.make_plan(), self.backend)
        result = self.check()
        issue = next(i for i in result['issues'] if i['reason'] == 'preserved_human_change')
        self.assertEqual(issue['severity'], 'info')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.remote()['tables']['channels']['records'][0]['fields']['fld_note'], 'Human correction')

    @case('integration', 'validation -> schema change', ('validation', 'schema'))
    def test_changed_schema_is_a_failure_instead_of_false_success(self):
        self.seed()
        self.edit_remote(lambda table: table['fields'][0].update(type='number'))
        result = self.check()
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(any(i['reason'] == 'table_snapshot_or_schema_failed' for i in result['issues']))

    @case('integration', 'validation -> missing identity cell', ('validation', 'identity'))
    def test_one_missing_identity_cell_has_one_actionable_warning(self):
        self.seed()
        rid = self.remote()['tables']['channels']['records'][0]['record_id']
        self.config(lambda c: c['roles']['channels'].update(required_on_create=['publisher']))
        self.edit_remote(lambda table: table['records'][0]['fields'].update(fld_publisher=''))
        result = self.check()
        warnings = [i for i in result['issues'] if i.get('record_id') == rid and i['severity'] == 'warning']
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]['field'], 'publisher')

    @case('integration', 'validation -> enum rules', ('validation', 'schema'))
    def test_unknown_csv_and_remote_select_values_are_reported(self):
        self.seed()
        self.config(lambda c: c['roles']['channels']['fields']['note'].update(type='select'))
        def change(table):
            next(f for f in table['fields'] if f['id'] == 'fld_note').update(
                type='select', multiple=True, options=[{'name': 'Allowed'}])
            for row in table['records']: row['fields']['fld_note'] = ['Unknown']
        self.edit_remote(change)
        result = self.check()
        reasons = {i['reason'] for i in result['issues']}
        self.assertTrue({'invalid_remote_value', 'invalid_csv_value'} <= reasons)

    @case('e2e', 'validate CLI -> malformed input -> partial report', ('validation', 'input'))
    def test_bad_csv_still_produces_a_report_and_no_queue(self):
        self.seed()
        self.config(lambda c: c.update(allow_writes=False))
        self.edit_csv(lambda rows: rows.append(deepcopy(rows[0])))
        result = main(['validate', '--config', str(self.config_path), '--date', '2026-11-13'])
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(any(i['reason'] == 'invalid_input' for i in result['issues']))
        self.assertFalse((self.state.root / 'research').exists())
        self.assertFalse((self.state.root / 'requests').exists())

    @case('integration', 'service validate -> CLI -> readonly report', ('validation', 'deployment'))
    def test_validate_service_uses_no_model_and_cannot_enable_writes(self):
        self.seed()
        self.config(lambda c: c.update(allow_writes=False))
        runtime = self.root / 'validation-service'
        service.install(runtime, self.config_path, mode='validate', at='12:00')
        report = service.tick(runtime, '2026-11-13')
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['result']['remote_writes'], 0)
        config = read_json(self.config_path); config['allow_writes'] = True
        write_json(self.config_path, config)
        with self.assertRaisesRegex(ResearchError, 'write-enabled'):
            service.tick(runtime, '2026-11-13')

    @case(target='common.load_config', tags=('validation', 'migration'))
    def test_old_model_command_cannot_silently_start_research(self):
        with self.assertRaisesRegex(ResearchError, 'removed'):
            self.config(lambda c: c.update(agent={'command': ['codex']}))
