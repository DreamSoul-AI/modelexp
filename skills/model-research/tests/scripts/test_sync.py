import copy
from pathlib import Path

from support import Workspace, case
from common import ResearchError
from evidence import dossier_path, read_dossier, save_dossier
import sync


class SyncTests(Workspace):
    @case('integration', 'ingest -> sync.apply -> FileAdapter', ('idempotency',))
    def test_apply_then_reingest_has_no_duplicate_creates_or_updates(self):
        self.seed()
        second = self.make_plan()
        self.assertEqual(second['operations'], [])
        self.assertEqual(len(self.remote()['tables']['channels']['records']), 2)

    @case('integration', 'sync.plan', ('conflict',))
    def test_both_sides_changed_keeps_human_change(self):
        self.seed()
        self.edit_remote(lambda t: t['records'][0]['fields'].update(fld_note='人工修改'))
        self.edit_csv(lambda rows: rows[0].update(备注='上游修改'))
        plan = self.make_plan()
        self.assertTrue(any(x['reason'] == 'both_sides_changed' for x in plan['issues']))
        sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(self.remote()['tables']['channels']['records'][0]['fields']['fld_note'], '人工修改')

    @case('integration', 'sync.plan -> evidence.save_dossier', ('mirror',))
    def test_only_remote_changed_updates_local_mirror_without_cloud_write(self):
        self.seed()
        self.edit_remote(lambda t: t['records'][0]['fields'].update(fld_note='人工修改'))
        plan = self.make_plan()
        self.assertEqual([op['kind'] for op in plan['operations']], ['mirror'])
        result = sync.apply(self.cfg, self.state, plan, self.backend)
        path = dossier_path(self.state, plan['operations'][0]['entity_id'])
        self.assertEqual(read_dossier(path)[0]['controlled_fields']['note']['value'], '人工修改')
        self.assertEqual(result['counts'], {'verified_local': 1})

    @case('integration', 'sync.plan', ('manual',))
    def test_manual_policy_never_overwrites_remote_field(self):
        self.seed()
        self.config(lambda c: c['roles']['channels']['fields']['note'].update(policy='manual'))
        self.edit_csv(lambda rows: rows[0].update(备注='not authorized'))
        plan = self.make_plan()
        self.assertTrue(any(x['reason'] == 'protected_or_unassigned' for x in plan['issues']))
        self.assertFalse(any('note' in x['fields'] for x in plan['operations']))

    @case('integration', 'sync.apply', ('recovery',))
    def test_receipt_lost_after_create_is_reconciled_without_duplicate(self):
        plan = self.make_plan()
        backend = self.backend
        original = backend.create
        calls = []
        def create_then_crash(role, spec, values):
            calls.append(1)
            original(role, spec, values)
            raise OSError('simulated lost acknowledgement')
        backend.create = create_then_crash
        first = sync.apply(self.cfg, self.state, plan, backend)
        self.assertEqual(first['counts'], {'unknown': 2})
        backend.create = original
        self.state.close()
        from state import State
        self.state = State(self.cfg['_state'])
        second = sync.apply(self.cfg, self.state, plan, backend)
        self.assertEqual(second['counts'], {'reconciled': 2})
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(self.remote()['tables']['channels']['records']), 2)

    @case('integration', 'sync.apply', ('recovery',))
    def test_unknown_create_without_observed_record_does_not_retry(self):
        plan = self.make_plan()
        calls = []
        def failed(role, spec, values):
            calls.append(1)
            raise OSError('request outcome not known')
        self.backend.create = failed
        sync.apply(self.cfg, self.state, plan, self.backend)
        sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.remote()['tables']['channels']['records'], [])

    @case('integration', 'sync.apply', ('preconditions',))
    def test_remote_edit_after_plan_is_not_overwritten(self):
        self.seed()
        self.edit_csv(lambda rows: rows[0].update(备注='AI update'))
        plan = self.make_plan()
        self.edit_remote(lambda t: t['records'][0]['fields'].update(fld_note='human after plan'))
        report = sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(report['counts'], {'conflict': 1})
        self.assertEqual(self.remote()['tables']['channels']['records'][0]['fields']['fld_note'], 'human after plan')

    @case('integration', 'sync.apply', ('preconditions',))
    def test_schema_change_after_plan_blocks_write(self):
        plan = self.make_plan()
        self.edit_remote(lambda t: t['fields'][0].update(name='renamed'))
        report = sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(report['counts'], {'conflict': 2})
        self.assertEqual(self.remote()['tables']['channels']['records'], [])

    @case(target='sync.check_plan', tags=('integrity',))
    def test_modified_plan_is_rejected(self):
        plan = self.make_plan()
        plan['operations'][0]['fields']['name'] = 'tampered'
        with self.assertRaisesRegex(ResearchError, 'modified'):
            sync.apply(self.cfg, self.state, plan, self.backend)

    @case(target='sync.check_plan', tags=('integrity',))
    def test_immutable_input_tamper_is_rejected(self):
        batch = self.batch()
        plan = sync.plan(self.cfg, self.state, batch, self.backend)
        Path(batch['sources'][0]['path']).write_text('corrupt')
        with self.assertRaisesRegex(ResearchError, 'source'):
            sync.apply(self.cfg, self.state, plan, self.backend)

    @case(target='sync.apply', tags=('policy',))
    def test_writes_disabled_blocks_all_mutations(self):
        self.config(lambda c: c.update(allow_writes=False))
        plan = self.make_plan()
        with self.assertRaisesRegex(ResearchError, 'allow_writes'):
            sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(self.remote()['tables']['channels']['records'], [])

    @case(target='sync.apply', tags=('readiness',))
    def test_unconfirmed_producer_blocks_apply_unless_explicitly_allowed(self):
        self.config(lambda c: c.update(allow_unconfirmed_input=False))
        plan = self.make_plan()
        with self.assertRaisesRegex(ResearchError, 'readiness'):
            sync.apply(self.cfg, self.state, plan, self.backend)

    @case(target='sync.plan', tags=('identity',))
    def test_duplicate_remote_identity_is_not_guessed(self):
        self.seed()
        self.edit_remote(lambda t: t['records'].append({**copy.deepcopy(t['records'][0]), 'record_id': 'rec_duplicate'}))
        plan = self.make_plan()
        self.assertTrue(any(x['reason'] == 'ambiguous_remote_identity' for x in plan['issues']))

    @case(target='sync.plan', tags=('identity',))
    def test_deleted_mapped_record_is_not_recreated(self):
        self.seed()
        self.edit_remote(lambda t: t['records'].pop(0))
        plan = self.make_plan()
        self.assertTrue(any(x['reason'] == 'remote_mapping_changed_requires_adoption' for x in plan['issues']))
        self.assertEqual(plan['operations'], [])

    @case(target='sync.apply', tags=('readback',))
    def test_failed_readback_does_not_advance_baseline(self):
        plan = self.make_plan()
        original = self.backend.create
        def create_wrong(role, spec, values):
            return original(role, spec, {**values, 'fld_note': 'server changed value'})
        self.backend.create = create_wrong
        report = sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(report['counts'], {'unknown': 2})
        self.assertFalse(self.state.baseline(plan['operations'][0]['entity_id'], 'note')[0])

    @case(target='sync.apply', tags=('local',))
    def test_dossier_proposal_changed_after_plan_blocks_write(self):
        plan = self.make_plan()
        op = plan['operations'][0]
        path = dossier_path(self.state, op['entity_id'])
        header, body = read_dossier(path)
        header['controlled_fields']['note'] = {'value': 'edited', 'evidence_ids': []}
        save_dossier(path, header, body)
        report = sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(report['counts'].get('conflict'), 1)
        self.assertEqual(len(self.remote()['tables']['channels']['records']), 1)

    @case(target='sync.schema_fingerprint', tags=('schema',))
    def test_schema_display_order_changes_do_not_block_safe_write(self):
        plan = self.make_plan()
        self.edit_remote(lambda t: t['fields'].reverse())
        self.assertEqual(sync.apply(self.cfg, self.state, plan, self.backend)['counts'], {'verified': 2})

    @case(target='sync.plan', tags=('recovery',))
    def test_new_batch_cannot_bypass_unknown_submission(self):
        plan = self.make_plan()
        def failed(*args):
            raise OSError('uncertain')
        self.backend.create = failed
        sync.apply(self.cfg, self.state, plan, self.backend)
        self.edit_csv(lambda rows: rows[0].update(备注='another candidate'))
        next_plan = self.make_plan()
        self.assertEqual(next_plan['operations'], [])
        self.assertEqual(sum(x['reason'] == 'pending_submission_requires_reconciliation' for x in next_plan['issues']), 2)

    @case('integration', 'sync.proposal', ('mirror',))
    def test_new_upstream_version_after_mirror_is_not_silently_ignored(self):
        self.seed()
        self.edit_remote(lambda t: t['records'][0]['fields'].update(fld_note='human'))
        sync.apply(self.cfg, self.state, self.make_plan(), self.backend)
        self.edit_csv(lambda rows: rows[0].update(备注='new upstream'))
        plan = self.make_plan()
        self.assertEqual([x['kind'] for x in plan['operations']], ['update'])
        sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(self.remote()['tables']['channels']['records'][0]['fields']['fld_note'], 'new upstream')

    @case(target='sync.plan', tags=('policy',))
    def test_empty_structured_candidate_cannot_bypass_clear_policy(self):
        self.seed()
        self.edit_csv(lambda rows: rows[0].update(备注='not empty'))
        batch = self.batch()
        path = dossier_path(self.state, batch['items'][0]['entity_id'])
        meta, body = read_dossier(path)
        from common import digest
        entry = {'evidence_id': 'clear', 'url': 'https://example.org/clear', 'kind': 'source_statement',
                 'excerpt': 'Fixture.', 'observed_at': '2026-11-14T00:00:00Z', 'content_sha256': digest('Fixture.')}
        meta['controlled_fields']['note'] = {'value': '', 'evidence_ids': ['clear'], 'evidence': [entry]}
        save_dossier(path, meta, body)
        plan = sync.plan(self.cfg, self.state, batch, self.backend)
        self.assertEqual(plan['operations'], [])
        self.assertTrue(any(x['reason'] == 'clear_not_enabled' for x in plan['issues']))

    @case(target='sync.plan', tags=('types', 'partial'))
    def test_invalid_field_candidate_does_not_abort_independent_entities(self):
        batch = self.batch()
        path = dossier_path(self.state, batch['items'][0]['entity_id'])
        meta, body = read_dossier(path)
        meta['controlled_fields']['note'] = {'value': ['wrong text type'], 'evidence_ids': [], 'evidence': []}
        save_dossier(path, meta, body)
        plan = sync.plan(self.cfg, self.state, batch, self.backend)
        self.assertTrue(any(x['reason'] == 'invalid_candidate_or_remote_value' for x in plan['issues']))
        self.assertTrue(any(x['entity_id'] == batch['items'][1]['entity_id'] for x in plan['operations']))
