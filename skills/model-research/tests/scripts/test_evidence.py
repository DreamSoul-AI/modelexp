from support import Workspace, case
from common import ResearchError, write_json
from evidence import dossier_path, import_candidates, read_dossier, save_dossier
import sync


class EvidenceTests(Workspace):
    def packet(self, field=None, evidence=None):
        batch = self.batch()
        item = batch['items'][0]
        data = {'schema_version': 1, 'batch_id': batch['batch_id'],
                'evidence': evidence or [{'evidence_id': 'official1', 'url': 'https://example.org/release',
                  'kind': 'source_statement', 'excerpt': 'Documented behavior.', 'observed_at': '2026-11-13T10:00:00+08:00'}],
                'items': [{'entity_id': item['entity_id'], 'fields': field or {'note': {'value': 'new evidence', 'evidence_ids': ['official1']}}}]}
        path = self.root / 'candidates.json'
        write_json(path, data)
        return batch, path, data

    @case('integration', 'evidence.import_candidates -> sync.plan', ('evidence',))
    def test_evidence_linked_candidate_becomes_controlled_value(self):
        batch, path, _ = self.packet()
        result = import_candidates(self.cfg, self.state, batch, path)
        self.assertEqual(result['imported_entities'], 1)
        plan = sync.plan(self.cfg, self.state, batch, self.backend)
        self.assertEqual(plan['operations'][0]['fields']['note'], 'new evidence')

    @case(target='evidence.import_candidates', tags=('evidence',))
    def test_missing_evidence_reference_is_rejected_before_dossier_change(self):
        batch, path, data = self.packet({'note': {'value': 'unsupported', 'evidence_ids': ['missing']}})
        original = dossier_path(self.state, batch['items'][0]['entity_id']).read_text()
        with self.assertRaisesRegex(ResearchError, 'evidence references'):
            import_candidates(self.cfg, self.state, batch, path)
        self.assertEqual(dossier_path(self.state, batch['items'][0]['entity_id']).read_text(), original)

    @case(target='evidence.import_candidates', tags=('boundary',))
    def test_candidate_cannot_target_an_unmapped_field(self):
        batch, path, _ = self.packet({'arbitrary_column': {'value': 'x', 'evidence_ids': ['official1']}})
        with self.assertRaisesRegex(ResearchError, 'unmapped'):
            import_candidates(self.cfg, self.state, batch, path)

    @case(target='evidence.import_candidates', tags=('protocol',))
    def test_score_requires_test_protocol_context(self):
        self.config(lambda c: c['roles']['channels']['fields']['note'].update(requires_context=['benchmark_version', 'inference_mode']))
        batch, path, _ = self.packet()
        with self.assertRaisesRegex(ResearchError, 'protocol context'):
            import_candidates(self.cfg, self.state, batch, path)

    @case(target='evidence.import_candidates', tags=('evidence',))
    def test_inference_is_not_accepted_as_official_evidence(self):
        batch, path, _ = self.packet(evidence=[{'evidence_id': 'official1', 'url': 'https://example.org',
             'kind': 'inference', 'excerpt': 'Maybe.', 'observed_at': '2026-11-13T10:00:00+08:00'}])
        with self.assertRaisesRegex(ResearchError, 'inference'):
            import_candidates(self.cfg, self.state, batch, path)

    @case('integration', 'evidence.prepare_dossiers', ('markdown',))
    def test_reingest_preserves_human_analysis_body(self):
        batch = self.batch()
        path = dossier_path(self.state, batch['items'][0]['entity_id'])
        meta, body = read_dossier(path)
        save_dossier(path, meta, body + '\nHuman analysis preserved.\n')
        self.edit_csv(lambda rows: rows[0].update(备注='upstream changed'))
        self.batch()
        self.assertIn('Human analysis preserved.', read_dossier(path)[1])

    @case('integration', 'evidence.import_candidates -> sync.apply', ('discoveries',))
    def test_agent_discovery_gets_its_own_identity_and_record(self):
        batch, path, data = self.packet()
        values = {'url': 'https://example.org/new', 'publisher': 'New Publisher', 'name': 'New Channel', 'note': 'documented'}
        data['discoveries'] = [{'role': 'channels', 'identity_values': values,
                                'fields': {k: {'value': v, 'evidence_ids': ['official1']} for k, v in values.items()}}]
        write_json(path, data)
        import_candidates(self.cfg, self.state, batch, path)
        plan = sync.plan(self.cfg, self.state, batch, self.backend)
        report = sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(report['counts'], {'verified': 3})

    @case(target='evidence.import_candidates', tags=('validation',))
    def test_malformed_candidate_is_a_controlled_error_before_mutation(self):
        batch, path, _ = self.packet({'note': 'not an object'})
        original = dossier_path(self.state, batch['items'][0]['entity_id']).read_text()
        with self.assertRaisesRegex(ResearchError, 'object'):
            import_candidates(self.cfg, self.state, batch, path)
        self.assertEqual(dossier_path(self.state, batch['items'][0]['entity_id']).read_text(), original)

    @case(target='evidence.import_candidates', tags=('validation',))
    def test_duplicate_evidence_references_are_rejected(self):
        batch, path, _ = self.packet({'note': {'value': 'x', 'evidence_ids': ['official1', 'official1']}})
        with self.assertRaisesRegex(ResearchError, 'evidence references'):
            import_candidates(self.cfg, self.state, batch, path)
