from support import Workspace, case
from common import ResearchError, write_json
from evidence import dossier_path, import_candidates, read_dossier, save_dossier
from dossiers import BEGIN, END, generated_block


class DossierTests(Workspace):
    def packet(self, text='来源支持的范围说明。', expected=None):
        batch = self.batch()
        eid = batch['items'][0]['entity_id']
        data = {'schema_version': 1, 'batch_id': batch['batch_id'],
                'evidence': [{'evidence_id': 'source', 'url': 'https://example.org/readme', 'kind': 'source_statement',
                              'excerpt': 'Actual fixture source text.', 'observed_at': '2026-11-14T12:00:00+08:00'}],
                'items': [], 'dossiers': [{'entity_id': eid, 'status': 'researched', 'expected_generated_sha256': expected,
                                          'sections': [{'key': 'summary', 'markdown': text, 'evidence_ids': ['source']},
                                                       {'key': 'uncertainties', 'markdown': '未进行本项目实测。', 'evidence_ids': []}]}]}
        path = self.root/'report.json'
        write_json(path, data)
        return batch, eid, path, data

    @case('integration', 'import_candidates -> dossiers.merge_report', ('markdown',))
    def test_research_report_is_readable_markdown_with_source_links_and_index(self):
        batch, eid, path, _ = self.packet()
        result = import_candidates(self.cfg, self.state, batch, path)
        meta, body = read_dossier(dossier_path(self.state, eid))
        self.assertEqual(result['dossier_count'], 1)
        self.assertEqual(meta['research']['status'], 'researched')
        self.assertIn('来源支持的范围说明。', body)
        self.assertIn('[source](https://example.org/readme)', body)
        self.assertIn(eid+'.md', (self.root/'state/dossiers/README.md').read_text())

    @case('integration', 'dossiers.merge_report', ('markdown', 'manual'))
    def test_human_notes_outside_generated_section_survive_updates(self):
        batch, eid, path, _ = self.packet()
        import_candidates(self.cfg, self.state, batch, path)
        file = dossier_path(self.state, eid)
        meta, body = read_dossier(file)
        save_dossier(file, meta, body+'\n## 我的笔记\n人工记录：保留这句话。\n')
        batch, _, path, _ = self.packet('更新后的来源说明。', meta['generated_block_sha256'])
        import_candidates(self.cfg, self.state, batch, path)
        updated = read_dossier(file)[1]
        self.assertIn('人工记录：保留这句话。', updated)
        self.assertIn('更新后的来源说明。', updated)
        self.assertEqual(updated.count(BEGIN), 1)

    @case('integration', 'dossiers.merge_report', ('markdown', 'conflict'))
    def test_manual_edit_inside_generated_section_is_not_overwritten(self):
        batch, eid, path, _ = self.packet()
        import_candidates(self.cfg, self.state, batch, path)
        file = dossier_path(self.state, eid)
        meta, body = read_dossier(file)
        body = body.replace('来源支持的范围说明。', '人工修正。')
        save_dossier(file, meta, body)
        batch, _, path, _ = self.packet('另一个自动版本。', meta['generated_block_sha256'])
        result = import_candidates(self.cfg, self.state, batch, path)
        self.assertEqual(result['conflicts'][0]['reason'], 'human_edited_generated_section')
        self.assertEqual(read_dossier(file)[1], body)
        self.assertTrue(list((self.root/'state/conflicts/markdown').glob('*.json')))

    @case(target='dossiers.merge_report', tags=('markdown', 'conflict'))
    def test_stale_research_result_is_kept_as_conflict(self):
        batch, eid, path, _ = self.packet()
        import_candidates(self.cfg, self.state, batch, path)
        batch, _, path, _ = self.packet('旧任务晚到。', None)
        result = import_candidates(self.cfg, self.state, batch, path)
        self.assertEqual(result['conflicts'][0]['reason'], 'dossier_changed_since_research_request')

    @case(target='dossiers.validate_report', tags=('evidence',))
    def test_missing_markdown_evidence_is_rejected_before_any_mutation(self):
        batch, eid, path, data = self.packet()
        original = dossier_path(self.state, eid).read_text()
        data['dossiers'][0]['sections'][0]['evidence_ids'] = ['not_read']
        write_json(path, data)
        with self.assertRaisesRegex(ResearchError, 'evidence references'):
            import_candidates(self.cfg, self.state, batch, path)
        self.assertEqual(dossier_path(self.state, eid).read_text(), original)

    @case(target='dossiers.validate_report', tags=('evidence',))
    def test_no_sources_cannot_be_reported_as_finished_research(self):
        batch, eid, path, data = self.packet()
        data['dossiers'][0]['sections'] = [data['dossiers'][0]['sections'][1]]
        write_json(path, data)
        with self.assertRaisesRegex(ResearchError, 'requires source evidence'):
            import_candidates(self.cfg, self.state, batch, path)

    @case(target='dossiers.validate_report', tags=('markdown',))
    def test_source_cannot_inject_generated_section_markers(self):
        batch, eid, path, _ = self.packet('untrusted '+END)
        with self.assertRaisesRegex(ResearchError, 'invalid dossier'):
            import_candidates(self.cfg, self.state, batch, path)

    @case(target='dossiers.merge_report', tags=('markdown', 'manual'))
    def test_human_deleted_generated_section_is_not_silently_recreated(self):
        batch, eid, path, _ = self.packet()
        import_candidates(self.cfg, self.state, batch, path)
        file = dossier_path(self.state, eid)
        meta, body = read_dossier(file)
        save_dossier(file, meta, body.replace(generated_block(body), ''))
        batch, _, path, _ = self.packet('recreate', meta['generated_block_sha256'])
        result = import_candidates(self.cfg, self.state, batch, path)
        self.assertEqual(result['conflicts'][0]['reason'], 'human_removed_generated_section')
