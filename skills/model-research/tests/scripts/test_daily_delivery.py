import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace

from support import case
from common import ResearchError
from daily_delivery import csv_rows, file_receipt, publish, unique_item, verify_rows
from daily_history import entity_keys, has_history_match, history_file_rows
from daily_producer import candidate_rows
from lark_adapter import UncertainWrite


class DeliveryTests(unittest.TestCase):
    @case(target='daily_delivery.csv_rows', tags=('delivery', 'format'))
    def test_csv_preserves_quoted_newlines_and_requires_original_column_order(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'example.csv'
            with path.open('w', encoding='utf-8-sig', newline='') as f:
                csv.writer(f).writerows([['名称', '说明'], ['A', '带逗号,\n和换行']])
            self.assertEqual(csv_rows(path, ['名称', '说明']), [{'名称': 'A', '说明': '带逗号,\n和换行'}])
            with self.assertRaisesRegex(ResearchError, 'field order'):
                csv_rows(path, ['说明', '名称'])

    @case(target='daily_delivery.verify_rows', tags=('delivery', 'identity', 'numeric'))
    def test_duplicate_ids_and_prose_in_numeric_fields_cannot_pass_preflight(self):
        headers = ['来源', '版本', '显存']
        spec = {'identity': ['url', 'revision'], 'fields': {
            'url': {'field_id': 'url', 'type': 'text', 'column': '来源', 'identity_url': True},
            'revision': {'field_id': 'revision', 'type': 'text', 'column': '版本'},
            'memory': {'field_id': 'memory', 'type': 'number', 'column': '显存',
                       'policy': 'ai', 'accept_upstream': True},
        }}
        schema = [{'id': key, 'type': rule['type']} for key, rule in spec['fields'].items()]
        row = dict(zip(headers, ('https://example.org/repo', 'abc1234', '3.17')))
        self.assertEqual(verify_rows('artifacts', [row], headers, spec, schema), {})
        with self.assertRaisesRegex(ResearchError, 'duplicate'):
            verify_rows('artifacts', [row, row], headers, spec, schema)
        with self.assertRaisesRegex(ResearchError, 'numeric'):
            verify_rows('artifacts', [{**row, '显存': '3.17（bf16 7.39）'}], headers, spec, schema)

    @case(target='daily_delivery.unique_item', tags=('delivery', 'conflict'))
    def test_existing_name_cannot_resolve_to_multiple_objects_or_wrong_type(self):
        drive = SimpleNamespace(list_files=lambda _: [{'name': '2026-11-19', 'type': 'file'}])
        with self.assertRaisesRegex(ResearchError, 'ambiguous'):
            unique_item(drive, 'folder', '2026-11-19', 'folder')
        drive.list_files = lambda _: [{'name': 'day.csv', 'type': 'file'}] * 2
        with self.assertRaisesRegex(ResearchError, 'ambiguous'):
            unique_item(drive, 'folder', 'day.csv', 'file')

    @case('integration', 'daily_delivery.publish -> lost response -> recovery', ('delivery', 'recovery'))
    def test_lost_upload_reply_is_reconciled_against_the_existing_markdown(self):
        day = '2026-11-19'
        name = 'models_org__repo_abc1234.md'
        with TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'md' / day / name
            path.parent.mkdir(parents=True)
            path.write_text('# Fixture\n')
            report = {'business_date': day, 'files': [file_receipt(path, root)]}
            cfg = {'roles': {'models': {'input': {'root_folder_token': 'root'}}}}
            folders = {'root': [{'name': 'md', 'type': 'folder', 'token': 'md'}],
                       'md': [{'name': day, 'type': 'folder', 'token': 'day'}], 'day': []}
            calls = []

            def submit(args, **_):
                calls.append(args)
                folders['day'].append({'name': name, 'type': 'file', 'token': 'written'})
                raise UncertainWrite('reply lost')

            drive = SimpleNamespace(list_files=lambda token: folders[token], call=submit,
                                    markdown_fetch=lambda _: path.read_text())
            journal = {'path': str(root / 'journal.json'), 'pending': [], 'verified': {}}
            with self.assertRaises(UncertainWrite):
                publish(cfg, drive, root, report, {}, journal)
            self.assertEqual(len(journal['pending']), 1)
            recovered = publish(cfg, drive, root, report, {}, journal)
            self.assertEqual(len(calls), 1)
            self.assertEqual(next(iter(recovered.values()))['token'], 'written')
            self.assertEqual(journal['pending'], [])

    @case(target='daily_history -> candidate_rows', tags=('delivery', 'deduplication'))
    def test_known_entity_is_not_reported_at_a_new_url_variant_or_revision(self):
        historical = history_file_rows('models', ('模型名称,获取地址\nOld name,https://hf.co/Org/Existing/tree/old\n').encode())
        history = {'models': historical[0], 'benchmarks': entity_keys(
            'benchmarks', 'Known-Bench', 'https://arxiv.org/abs/2611.12345v1')}
        excerpt = 'This is a real quote from the fixed version.'
        items = [{'id': 'm', 'role': 'models', 'url': 'https://huggingface.co/org/existing', 'excerpt': excerpt},
                 {'id': 'b', 'role': 'benchmarks', 'url': 'https://github.com/org/replacement', 'excerpt': excerpt}]
        base = {'include': True, 'publisher': '', 'intro': '简介', 'quote': excerpt, 'limitations': '', 'columns': []}
        decisions = [{**base, 'id': 'm', 'name': 'New title'},
                     {**base, 'id': 'b', 'name': 'Ｋnown BENCH'}]
        for item in items:
            item.update(repo='org/new-label', revision='a' * 40, source=item['url'])
        self.assertEqual(list(candidate_rows(items, decisions, history, {'models': [], 'benchmarks': []},
                                             '2026-11-20')), [])
        previous = entity_keys('artifacts', '4-bit', 'https://hf.co/Org/Q/blob/old/one.gguf')
        same = entity_keys('artifacts', 'other title', 'https://huggingface.co/org/q/resolve/new/one.gguf')
        different = entity_keys('artifacts', 'new title', 'https://huggingface.co/org/q/resolve/new/two.gguf')
        self.assertTrue(has_history_match(same, previous))
        self.assertFalse(has_history_match(different, previous))

    @case(target='daily_delivery.publish', tags=('delivery', 'conflict'))
    def test_daily_folder_from_another_producer_blocks_even_a_zero_new_day(self):
        day = '2026-11-20'
        folders = {'root': [{'name': 'md', 'type': 'folder', 'token': 'md'}],
                   'md': [{'name': day, 'type': 'folder', 'token': 'day'}],
                   'day': [{'name': 'models_org__existing_abc1234.md', 'type': 'file'}]}
        drive = SimpleNamespace(list_files=lambda token: folders[token])
        cfg = {'roles': {'models': {'input': {'root_folder_token': 'root'}}}}
        with self.assertRaisesRegex(ResearchError, 'outside this bundle'):
            publish(cfg, drive, Path('/unused'), {'business_date': day, 'files': []}, {}, {})
