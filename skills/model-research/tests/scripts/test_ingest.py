import csv
import hashlib
import json
from pathlib import Path

from support import Workspace, case
from common import ResearchError, write_json
from ingest import ingest


class IngestTests(Workspace):
    @case(target='ingest.ingest', tags=('idempotency',))
    def test_identical_csv_reuses_batch_identity(self):
        self.assertEqual(self.batch()['batch_id'], self.batch()['batch_id'])

    @case(target='ingest.ingest', tags=('version',))
    def test_same_filename_changed_content_has_new_batch_and_keeps_original(self):
        first = self.batch()
        old = Path(first['sources'][0]['path']).read_bytes()
        self.edit_csv(lambda rows: rows[0].update(备注='new content'))
        second = self.batch()
        self.assertNotEqual(first['batch_id'], second['batch_id'])
        self.assertEqual(Path(first['sources'][0]['path']).read_bytes(), old)

    @case(target='ingest.ingest', tags=('readiness',))
    def test_missing_required_file_waits_instead_of_treating_as_zero_rows(self):
        (self.root / 'incoming/channels_2026-11-13.csv').unlink()
        result = self.batch()
        self.assertEqual(result['status'], 'waiting_input')
        self.assertEqual(result['issues'][0]['reason'], 'missing_input')

    @case(target='ingest.ingest', tags=('identity',))
    def test_source_id_reassigned_is_retained_as_identity_conflict(self):
        self.batch()
        self.edit_csv(lambda rows: rows[0].update(入口链接='https://different.example.org'))
        result = self.batch()
        self.assertEqual(result['items'][0]['identity_conflict'], 'source_id_reassigned')

    @case(target='ingest.ingest', tags=('identity',))
    def test_duplicate_identity_in_input_is_rejected(self):
        self.edit_csv(lambda rows: rows.append(rows[0].copy()))
        with self.assertRaisesRegex(ResearchError, 'duplicate entity'):
            self.batch()

    @case(target='ingest.ingest', tags=('csv',))
    def test_csv_semicolon_notes_are_kept_as_text(self):
        result = self.batch()
        self.assertEqual(result['items'][0]['raw_fields']['note'], '演示数据；保留完整文本')

    @case(target='ingest.ingest', tags=('readiness',))
    def test_manifest_checks_hash_not_only_filename(self):
        path = self.root / 'producer.json'
        write_json(path, {'business_date': '2026-11-13', 'complete': True,
                         'files': {'channels': {'name': 'channels_2026-11-13.csv', 'sha256': 'wrong'}}})
        with self.assertRaisesRegex(ResearchError, 'hash mismatch'):
            self.batch(path)

    @case(target='ingest.ingest', tags=('readiness',))
    def test_valid_manifest_confirms_batch(self):
        path = self.root / 'producer.json'
        csv_path = self.root / 'incoming/channels_2026-11-13.csv'
        write_json(path, {'business_date': '2026-11-13', 'complete': True,
                         'files': {'channels': {'name': csv_path.name, 'sha256': hashlib.sha256(csv_path.read_bytes()).hexdigest()}}})
        self.assertEqual(self.batch(path)['readiness'], 'producer_confirmed')

    @case(target='ingest.ingest', tags=('scope',))
    def test_source_links_cannot_be_enabled_via_input_pattern(self):
        self.config(lambda c: c['roles']['channels']['input'].update(filename='source_links_*.csv'))
        with self.assertRaisesRegex(ResearchError, 'disabled'):
            self.batch()

    @case(target='ingest.columns_for', tags=('csv',))
    def test_missing_column_is_reported_instead_of_silently_dropped(self):
        self.config(lambda c: c['roles']['channels']['fields']['note'].update(column='missing'))
        with self.assertRaisesRegex(ResearchError, 'CSV column'):
            self.batch()

    @case(target='ingest.ingest', tags=('identity',))
    def test_missing_identity_keeps_independent_rows_and_reports_partial(self):
        self.edit_csv(lambda rows: rows[0].update(入口链接=''))
        batch = self.batch()
        self.assertEqual(len(batch['items']), 1)
        self.assertEqual(batch['status'], 'ready')
        self.assertEqual(batch['issues'][0]['reason'], 'unresolved_identity')

    @case(target='common.load_config', tags=('policy',))
    def test_string_false_cannot_enable_writes(self):
        from common import load_config, read_json
        cfg = read_json(self.config_path)
        cfg['allow_writes'] = 'false'
        write_json(self.config_path, cfg)
        with self.assertRaisesRegex(ResearchError, 'boolean'):
            load_config(self.config_path)
