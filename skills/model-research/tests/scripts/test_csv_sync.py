from unittest.mock import patch

from support import Workspace, case
from common import ResearchError
from evidence import dossier_path, read_dossier, save_dossier
from identity import source_value, url_identity
from lark_adapter import UncertainWrite
import sync


class CsvSyncTests(Workspace):
    def direct(self):
        def configure(cfg):
            cfg['backend']['batch_size'] = 200
            for field in cfg['roles']['channels']['fields'].values():
                field.update(accept_upstream=True, prefer_upstream=True)
        self.config(configure)

    @case(target='identity.source_value', tags=('csv', 'select'))
    def test_multi_select_commas_and_single_select_punctuation(self):
        field = {'type': 'select', 'multiple': True, 'options': [{'name': '文本输入'}, {'name': '文本输出'}]}
        self.assertEqual(source_value('文本输入，文本输出', field), ['文本输入', '文本输出'])
        field.update(multiple=False, options=[{'name': 'Team（A，B）'}])
        self.assertEqual(source_value('Team（A，B）', field), ['Team（A，B）'])
        with self.assertRaises(ResearchError):
            source_value('Unknown', field)

    @case(target='identity.source_value', tags=('csv', 'aliases'))
    def test_explicit_aliases_reuse_existing_option_names(self):
        field = {'type': 'select', 'multiple': False, 'options': [{'name': '测试集；评测框架'}]}
        self.assertEqual(source_value('测试集+评测框架', field,
                                     {'value_aliases': {'测试集+评测框架': '测试集；评测框架'}}), ['测试集；评测框架'])

    @case(target='identity.url_identity', tags=('csv', 'identity'))
    def test_first_official_url_is_an_explicit_column_contract(self):
        cell = 'https://huggingface.co/datasets/A/main；源数据 https://huggingface.co/datasets/B/other'
        with self.assertRaises(ResearchError):
            url_identity(cell)
        self.assertEqual(url_identity(cell, 'github.com', first=True), 'https://huggingface.co/datasets/A/main')

    @case(target='identity.source_value', tags=('csv', 'url'))
    def test_url_cell_receives_only_the_link_while_plain_text_keeps_details(self):
        cell = 'Org/Model；https://huggingface.co/Org/Model'
        rule = {'identity_url': True}
        self.assertEqual(source_value(cell, {'type': 'text', 'style': {'type': 'url'}}, rule),
                         'https://huggingface.co/Org/Model')
        self.assertEqual(source_value(cell, {'type': 'text'}, rule), cell)
        self.assertEqual(source_value('https://example.org', {'type': 'text', 'style': {'type': 'url'}}, rule),
                         'https://example.org')

    @case('integration', 'CSV -> batch submit -> readback -> repeat', ('csv', 'batching'))
    def test_bulk_create_uses_one_request_and_repeated_sync_does_not_duplicate(self):
        self.direct()
        with patch.object(self.backend, 'create_many', wraps=self.backend.create_many) as create:
            result = sync.apply(self.cfg, self.state, self.make_plan(), self.backend)
        self.assertEqual(result['counts'], {'verified': 2})
        self.assertEqual(create.call_count, 1)
        self.assertEqual(self.make_plan()['operations'], [])

    @case('integration', 'CSV preference -> protected mirror', ('csv', 'human'))
    def test_csv_overrides_stale_agent_candidate_but_keeps_human_edits_on_repeats(self):
        self.direct()
        batch = self.batch()
        path = dossier_path(self.state, batch['items'][0]['entity_id'])
        meta, body = read_dossier(path)
        meta['controlled_fields']['note'] = {'value': 'Old model guess'}
        save_dossier(path, meta, body)
        plan = sync.plan(self.cfg, self.state, batch, self.backend)
        first = next(op for op in plan['operations'] if op['entity_id'] == batch['items'][0]['entity_id'])
        self.assertNotEqual(first['fields']['note'], 'Old model guess')
        sync.apply(self.cfg, self.state, plan, self.backend)
        self.edit_remote(lambda table: table['records'][0]['fields'].update(fld_note='Human correction'))
        mirror = self.make_plan()
        sync.apply(self.cfg, self.state, mirror, self.backend)
        self.assertEqual(self.make_plan()['operations'], [])
        self.assertEqual(self.remote()['tables']['channels']['records'][0]['fields']['fld_note'], 'Human correction')

    @case('integration', 'bulk submit -> lost ack -> verify', ('csv', 'recovery'))
    def test_lost_batch_ack_is_reconciled_without_resubmission(self):
        self.direct()
        plan = self.make_plan()
        original = self.backend.create_many
        def lost(*args):
            original(*args)
            raise UncertainWrite('lost response')
        with patch.object(self.backend, 'create_many', side_effect=lost):
            result = sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(result['counts'], {'unknown': 2})
        with patch.object(self.backend, 'create_many') as create:
            checked = sync.apply(self.cfg, self.state, plan, self.backend, verify_only=True)
        create.assert_not_called()
        self.assertEqual(checked['counts'], {'reconciled': 2})

    @case('integration', 'bulk preflight -> remote human change', ('csv', 'human'))
    def test_bulk_write_rechecks_values_immediately_before_submit(self):
        self.direct()
        self.seed()
        self.edit_csv(lambda rows: rows[0].update(备注='New upstream'))
        plan = self.make_plan()
        real = self.backend.snapshot
        calls = 0
        def snapshot(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.edit_remote(lambda table: table['records'][0]['fields'].update(fld_note='Concurrent human edit'))
            return real(*args)
        with patch.object(self.backend, 'snapshot', side_effect=snapshot), patch.object(self.backend, 'update_many') as update:
            result = sync.apply(self.cfg, self.state, plan, self.backend)
        update.assert_not_called()
        self.assertEqual(result['counts'], {'conflict': 1})

    @case('integration', 'CSV direct run', ('csv', 'agent'))
    def test_csv_only_run_has_no_model_dependency(self):
        from research import main
        self.direct()
        result = main(['run', '--config', str(self.config_path), '--date', '2026-11-13', '--mode', 'apply'])
        self.assertFalse((self.state.root / 'requests').exists())
        self.assertFalse((self.state.root / 'research').exists())
        self.assertEqual(result['counts'], {'verified': 2})
