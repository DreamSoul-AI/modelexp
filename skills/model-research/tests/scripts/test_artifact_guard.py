from support import Workspace, case
from identity import identity
from sync import creation_blocker


class ArtifactGuardTests(Workspace):
    @case(target='sync.creation_blocker', tags=('identity', 'human', 'cache'))
    def test_text_cache_does_not_reuse_a_guard_decision_after_a_remote_name_edit(self):
        spec, item, fields, record = self.fixture()
        spec['allow_distinct_artifact_files'] = False
        record['fields']['n'] = 'Different name'
        self.assertIsNone(creation_blocker(item, spec, fields, [record], []))
        record['fields']['n'] = 'SAME-display NAME!'
        self.assertEqual(creation_blocker(item, spec, fields, [record], []), 'remote_name_or_alias_requires_adoption')
        record['fields']['n'] = 'Different name'
        self.assertIsNone(creation_blocker(item, spec, fields, [record], []))

    def fixture(self):
        spec={'identity':['url','revision'],'fields':{'url':{'field_id':'u','identity_url':True},'revision':{'field_id':'r'},'name':{'field_id':'n'}},'creation_guard_keys':['name'],'allow_distinct_artifact_files':True}
        raw={'url':'https://example.org/repo/tree/abc','revision':'abc\na.gguf sha256=1','name':'Same display name'}
        eid,parts=identity('artifacts',spec,raw)
        item={'role':'artifacts','entity_id':eid,'identity':parts,'raw_fields':raw}
        fields={k:{'id':v['field_id']} for k,v in spec['fields'].items()}
        record={'record_id':'r1','fields':{'u':raw['url'],'r':'abc\nb.gguf sha256=2','n':raw['name']}}
        return spec,item,fields,record

    @case(target='sync.creation_blocker', tags=('quant','identity'))
    def test_identified_distinct_files_can_share_a_display_name(self):
        spec,item,fields,record=self.fixture()
        self.assertIsNone(creation_blocker(item,spec,fields,[record],[]))
        spec['allow_distinct_artifact_files']=False
        self.assertEqual(creation_blocker(item,spec,fields,[record],[]),'remote_name_or_alias_requires_adoption')

    @case(target='sync.creation_blocker', tags=('quant','identity'))
    def test_incomplete_or_identical_identity_is_still_blocked(self):
        spec,item,fields,record=self.fixture()
        self.assertEqual(creation_blocker(item,spec,fields,[record],['r1']),'remote_name_or_alias_requires_adoption')
        record['fields']['r']=item['raw_fields']['revision']
        self.assertEqual(creation_blocker(item,spec,fields,[record],[]),'remote_name_or_alias_requires_adoption')
