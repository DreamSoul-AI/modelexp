import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from support import case
from common import ResearchError
from lark_adapter import LarkAdapter


class AdapterTests(unittest.TestCase):
    @case(target='lark_adapter.LarkAdapter.snapshot', tags=('scores', 'projection'))
    def test_more_than_fifty_fields_are_read_in_consistent_chunks(self):
        schema = [{'id': 'f'+str(i), 'name': 'N'+str(i), 'type': 'number'} for i in range(74)]
        calls = []
        def fake(args, cwd=None, **kwargs):
            if '+field-list' in args:return {'fields': schema}
            ids = [args[i+1] for i, a in enumerate(args) if a == '--field-id'];calls.append(len(ids))
            Path(cwd, args[args.index('--output')+1]).write_text(json.dumps(
                {'record_id': 'r', **{'N'+f[1:]: int(f[1:]) for f in ids}})+'\n')
            return {'base_token':'b','table_id':'t','rev':1,'query_context':{},'records_count':1,'has_more':False}
        self.adapter.call = fake
        _, records = self.adapter.snapshot('models', {'base_token':'b','table_id':'t',
            'fields': {f['id']:{'field_id':f['id']} for f in schema}})
        self.assertEqual(calls, [50,24])
        self.assertEqual(len(records[0]['fields']),74)

    @case(target='lark_adapter.LarkAdapter.snapshot', tags=('scores', 'projection'))
    def test_projection_revision_change_is_not_silently_merged(self):
        schema = [{'id': 'f'+str(i), 'name': 'N'+str(i), 'type': 'number'} for i in range(51)]
        call = 0
        def fake(args, cwd=None, **kwargs):
            nonlocal call
            if '+field-list' in args:return {'fields':schema}
            call += 1
            Path(cwd,args[args.index('--output')+1]).write_text('{"record_id":"r"}\n')
            return {'base_token':'b','table_id':'t','rev':call,'query_context':{},'records_count':1,'has_more':False}
        self.adapter.call = fake
        with self.assertRaisesRegex(ResearchError,'between field projections'):
            self.adapter.snapshot('models',{'base_token':'b','table_id':'t','fields':{f['id']:{'field_id':f['id']} for f in schema}})
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.adapter = LarkAdapter({'command': ['fake-lark']}, self.temp.name)

    @case(target='lark_adapter.LarkAdapter.call', tags=('manifest',))
    def test_ndjson_manifest_does_not_require_ok_field(self):
        result = subprocess.CompletedProcess([], 0, json.dumps({'manifest_version': 'v1', 'format': 'ndjson', 'records_count': 0}), '')
        with patch('lark_adapter.subprocess.run', return_value=result):
            self.assertEqual(self.adapter.call([], manifest=True)['records_count'], 0)

    @case(target='lark_adapter.LarkAdapter.call', tags=('privacy',))
    def test_stderr_does_not_leak_into_error(self):
        result = subprocess.CompletedProcess([], 5, '', 'secret_token_value')
        with patch('lark_adapter.subprocess.run', return_value=result):
            with self.assertRaises(ResearchError) as caught:
                self.adapter.call([])
        self.assertNotIn('secret_token_value', str(caught.exception))

    @case(target='lark_adapter.LarkAdapter.snapshot', tags=('pagination',))
    def test_all_pages_are_read_with_explicit_user_and_projection(self):
        calls = []
        def fake(args, cwd=None, manifest=False, write=False):
            calls.append(args)
            if '+field-list' in args:
                return {'fields': [{'id': 'fld_id', 'name': 'Name', 'type': 'text'}]}
            offset = int(args[args.index('--offset') + 1])
            output = args[args.index('--output') + 1]
            Path(cwd, output).write_text(json.dumps({'record_id': 'rec'+str(offset), 'Name': 'value'+str(offset)})+'\n')
            return {'base_token': 'base', 'table_id': 'table', 'rev': 1, 'query_context': {},
                    'records_count': 1, 'has_more': offset == 0, 'next_offset': offset + 1}
        self.adapter.call = fake
        _, records = self.adapter.snapshot('role', {'base_token': 'base', 'table_id': 'table', 'fields': {'name': {'field_id': 'fld_id'}}})
        self.assertEqual([r['record_id'] for r in records], ['rec0', 'rec1'])
        self.assertTrue(all(args[-2:] == ['--as', 'user'] or '--field-id' in args for args in calls))

    @case(target='lark_adapter.LarkAdapter.snapshot', tags=('pagination',))
    def test_revision_change_between_pages_is_rejected(self):
        def fake(args, cwd=None, manifest=False, write=False):
            if '+field-list' in args:
                return {'fields': [{'id': 'f', 'name': 'N', 'type': 'text'}]}
            offset = int(args[args.index('--offset')+1])
            Path(cwd, args[args.index('--output')+1]).write_text(json.dumps({'record_id': 'r'+str(offset), 'N': 'x'})+'\n')
            return {'base_token': 'b', 'table_id': 't', 'rev': offset, 'query_context': {},
                    'records_count': 1, 'has_more': True, 'next_offset': offset+1}
        self.adapter.call = fake
        with self.assertRaisesRegex(ResearchError, 'changed during pagination'):
            self.adapter.snapshot('role', {'base_token': 'b', 'table_id': 't', 'fields': {'x': {'field_id': 'f'}}})

    @case(target='lark_adapter.LarkAdapter.schema', tags=('schema', 'pagination'))
    def test_truncated_option_list_is_completed_across_pages(self):
        calls = []
        def fake(args, **kwargs):
            calls.append(args)
            if '+field-list' in args:
                return {'fields': [{'id': 'f', 'type': 'select', 'name': 'Publisher',
                                    'options': [{'name': 'first'}], 'truncated': True}]}
            offset = int(args[args.index('--offset') + 1])
            return {'total': 3, 'options': [{'name': name} for name in (['first', 'second'] if offset == 0 else ['third'])]}
        self.adapter.call = fake
        fields = self.adapter.schema({'base_token': 'b', 'table_id': 't', 'fields': {'publisher': {'field_id': 'f'}}})
        self.assertEqual([o['name'] for o in fields[0]['options']], ['first', 'second', 'third'])
        self.assertNotIn('truncated', fields[0])
        self.assertEqual(len(calls), 3)

    @case(target='lark_adapter.LarkAdapter.schema', tags=('schema', 'pagination'))
    def test_incomplete_option_pagination_is_rejected(self):
        def fake(args, **kwargs):
            if '+field-list' in args:
                return {'fields': [{'id': 'f', 'type': 'select', 'options': [], 'remaining_options_count': 99}]}
            return {'options': [], 'total': 99}
        self.adapter.call = fake
        with self.assertRaisesRegex(ResearchError, 'did not advance'):
            self.adapter.schema({'base_token': 'b', 'table_id': 't', 'fields': {'x': {'field_id': 'f'}}})

    @case(target='lark_adapter.LarkAdapter.append_select_options', tags=('csv', 'schema'))
    def test_option_append_preserves_existing_names_and_field_properties(self):
        before = {'id': 'f', 'type': 'select', 'name': 'Publisher', 'multiple': False,
                  'description': 'Original description', 'default_value': None,
                  'options': [{'name': 'first', 'hue': 'Green'}, {'name': 'second'}]}
        after = {**before, 'options': before['options'] + [{'name': 'third'}]}
        calls = []
        def fake(args, cwd=None, **kwargs):
            calls.append(args)
            if '+field-get' in args:
                return {'field': before}
            body = json.loads(Path(cwd, 'request.json').read_text())
            self.assertEqual(body['description'], 'Original description')
            self.assertEqual(body['options'][:2], before['options'])
            self.assertEqual(body['options'][2:], [{'name': 'third'}])
            return {}
        self.adapter.call = fake
        with patch.object(self.adapter, 'schema', side_effect=[[before], [after]]):
            added = self.adapter.append_select_options({'base_token': 'b', 'table_id': 't'}, 'f', ['second', 'third'])
        self.assertEqual(added, ['third'])
        self.assertIn('--dry-run', calls[1])
        self.assertIn('--yes', calls[2])

    @case(target='lark_adapter.LarkAdapter.snapshot', tags=('scores','pagination'))
    def test_more_than_fifty_fields_are_joined_by_record_identity(self):
        fields=[{'id':'f'+str(i),'name':'N'+str(i),'type':'text'} for i in range(74)]
        self.adapter.schema=lambda spec: fields
        projections=[]
        def projection(spec,ids,names):
            projections.append(ids)
            return [{'record_id':'r','fields':{i:names[i] for i in ids}}],7
        self.adapter._projection=projection
        _,records=self.adapter.snapshot('models',{'fields':{f['id']:{'field_id':f['id']} for f in fields}})
        self.assertEqual([len(p) for p in projections],[50,24]);self.assertEqual(len(records[0]['fields']),74)

    @case(target='lark_adapter.LarkAdapter.snapshot', tags=('scores','pagination'))
    def test_projection_revision_change_rejects_inconsistent_snapshot(self):
        fields=[{'id':'f'+str(i),'name':'N'+str(i),'type':'text'} for i in range(51)]
        self.adapter.schema=lambda spec:fields
        self.adapter._projection=lambda spec,ids,names:([{'record_id':'r','fields':{i:'v' for i in ids}}],len(ids))
        with self.assertRaisesRegex(ResearchError,'between field projections'):
            self.adapter.snapshot('models',{'fields':{f['id']:{'field_id':f['id']} for f in fields}})
