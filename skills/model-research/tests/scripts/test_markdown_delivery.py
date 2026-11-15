from pathlib import Path

from support import Workspace, case
from common import ResearchError, digest, read_json, write_json
from dossiers import BEGIN, END, clean_layout, generated_block
from evidence import dossier_path, import_candidates, read_dossier, save_dossier
import markdown_delivery


class MarkdownDeliveryTests(Workspace):
    def generated(self):
        batch = self.batch()
        eid = batch['items'][0]['entity_id']
        file = dossier_path(self.state, eid)
        meta, body = read_dossier(file)
        block = BEGIN + '\n## 自动调研记录\n\n实际来源整理。\n\n依据：https://example.org/model-card\n\n未实测。\n' + END
        meta.update(generated_block_sha256=digest(block), research={'status': 'researched'})
        save_dossier(file, meta, body + '\n' + block)
        return dossier_path(self.state, eid)

    @case(target='dossiers.clean_layout', tags=('markdown', 'manual'))
    def test_exact_legacy_placeholders_are_removed_but_input_and_notes_survive(self):
        body = '# 资料档案\n\n## 结论与适用范围\n\n待查证；上游 CSV 信息不是已核实结论。\n\n'
        body += '## 输入资料（未核验）\n\n```json\n{"name":"A"}\n```\n\n'
        body += '## 评测条件与可比性\n\n待补。\n\n## 我的笔记\n\n保留人工笔记。\n'
        result = clean_layout({'entity_id': 'id', 'display_name': 'Model A'}, body)
        self.assertTrue(result.startswith('# Model A'))
        self.assertNotIn('待补。', result)
        self.assertNotIn('## 结论与适用范围', result)
        self.assertIn('{"name":"A"}', result)
        self.assertIn('## 我的笔记\n\n保留人工笔记。', result)

    @case(target='dossiers.clean_layout', tags=('markdown', 'manual'))
    def test_user_expanded_section_and_fenced_examples_are_preserved(self):
        body = '# My own title\n\n## 评测条件与可比性\n\n待补。\n\n我的补充。\n\n'
        body += '## Example\n\n```markdown\n# 资料档案\n## 评测条件与可比性\n\n待补。\n```\n'
        self.assertEqual(clean_layout({'entity_id': 'id', 'display_name': 'A'}, body), body)

    @case('integration', 'finalize Markdown -> protected generation fingerprint', ('markdown', 'migration'))
    def test_finalize_is_idempotent_and_keeps_backup_and_generated_block_unchanged(self):
        file = self.generated()
        meta, body = read_dossier(file)
        original_block = generated_block(body)
        legacy = body + '\n## 评测条件与可比性\n\n待补。\n'
        meta.pop('document_layout_version', None)
        save_dossier(file, meta, legacy)
        original = file.read_text()
        result = markdown_delivery.finalize(self.state)
        updated_meta, updated_body = read_dossier(file)
        self.assertEqual(generated_block(updated_body), original_block)
        self.assertEqual(updated_meta['generated_block_sha256'], digest(original_block))
        self.assertNotIn('待补。', updated_body)
        self.assertEqual((Path(result['backup']) / file.name).read_text(), original)
        self.assertEqual(markdown_delivery.finalize(self.state)['changed'], 0)

    @case('integration', 'finalize Markdown -> manual conflict', ('markdown', 'manual'))
    def test_finalize_does_not_touch_human_edited_generated_text(self):
        file = self.generated()
        meta, body = read_dossier(file)
        save_dossier(file, meta, body.replace('实际来源整理。', '人工修正。'))
        original = file.read_text()
        result = markdown_delivery.finalize(self.state)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(file.read_text(), original)

    @case('integration', 'export readable Markdown snapshot', ('markdown', 'export'))
    def test_export_contains_research_and_sources_without_raw_input_metadata_or_notes(self):
        file = self.generated()
        meta, body = read_dossier(file)
        save_dossier(file, meta, body + '\n## 人工私有笔记\n不要发布这一段。\n')
        dest = self.root / 'public-reports'
        result = markdown_delivery.export(self.state, dest)
        self.assertEqual(result['reports'], 1)
        exported = (dest / file.name).read_text()
        self.assertTrue(exported.startswith('# '))
        self.assertIn('实际来源整理。', exported)
        self.assertIn('https://example.org/model-card', exported)
        self.assertNotIn('controlled_fields', exported)
        self.assertNotIn('输入资料', exported)
        self.assertNotIn('不要发布这一段', exported)
        self.assertNotIn(BEGIN, exported)
        self.assertIn(file.name, (dest / 'README.md').read_text())
        snapshot = read_json(dest / 'snapshot.json')
        self.assertEqual(snapshot['reports'][0]['status'], 'researched')
        self.assertEqual(markdown_delivery.export(self.state, dest)['reports'], 1)

    @case('integration', 'export protects human file changes', ('markdown', 'export', 'manual'))
    def test_export_refuses_to_overwrite_user_changes_or_unrelated_files(self):
        self.generated()
        dest = self.root / 'reports'
        markdown_delivery.export(self.state, dest)
        (dest / 'README.md').write_text('Human changes')
        with self.assertRaisesRegex(ResearchError, 'human edits'):
            markdown_delivery.export(self.state, dest)
        unrelated = self.root / 'unrelated'
        unrelated.mkdir()
        (unrelated / 'README.md').write_text('Existing file')
        with self.assertRaisesRegex(ResearchError, 'unrelated file'):
            markdown_delivery.export(self.state, unrelated)
        self.assertEqual((unrelated / 'README.md').read_text(), 'Existing file')

    @case('integration', 'export validates generation provenance', ('markdown', 'export'))
    def test_export_rejects_edited_generated_content_and_private_state_destination(self):
        file = self.generated()
        with self.assertRaisesRegex(ResearchError, 'separate directories'):
            markdown_delivery.export(self.state, self.state.root / 'public')
        meta, body = read_dossier(file)
        save_dossier(file, meta, body.replace('实际来源整理。', 'Modified'))
        with self.assertRaisesRegex(ResearchError, 'requires review'):
            markdown_delivery.export(self.state, self.root / 'reports')

    @case(target='markdown_delivery.export', tags=('markdown', 'pending'))
    def test_input_only_templates_are_not_exported_as_completed_research(self):
        self.batch()
        result = markdown_delivery.export(self.state, self.root / 'reports')
        self.assertEqual(result['reports'], 0)
        self.assertEqual(result['without_research'], 2)
