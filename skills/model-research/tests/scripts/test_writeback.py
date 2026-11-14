from unittest.mock import patch
from support import Workspace, case
from common import read_json, write_json
from ingest import ingest
from identity import url_identity
import sys
import sync


class WritebackTests(Workspace):
    @case('integration','ingest observations -> sync readiness',('readiness','writeback'))
    def test_inputs_require_two_identical_observations_separated_in_time(self):
        self.config(lambda c:c.update(allow_unconfirmed_input=False,input_readiness={'strategy':'stable_observations','min_interval_seconds':60}))
        with patch('ingest.now',return_value='2026-11-14T15:00:00+08:00'):
            first=self.batch()
        self.assertEqual(first['readiness'],'observing')
        with patch('ingest.now',return_value='2026-11-14T15:00:30+08:00'):
            self.assertEqual(self.batch()['readiness'],'observing')
        with patch('ingest.now',return_value='2026-11-14T15:01:01+08:00'):
            stable=self.batch()
        self.assertEqual(stable['readiness'],'observed_stable')
        self.assertNotEqual(first['batch_id'],stable['batch_id'])
        plan=sync.plan(self.cfg,self.state,stable,self.backend)
        self.assertEqual(sync.apply(self.cfg,self.state,plan,self.backend)['counts'],{'verified':2})

    @case(target='ingest.ingest',tags=('readiness','version'))
    def test_changed_content_resets_stability_clock(self):
        self.config(lambda c:c.update(input_readiness={'strategy':'stable_observations','min_interval_seconds':60}))
        with patch('ingest.now',return_value='2026-11-14T15:00:00+08:00'):self.batch()
        self.edit_csv(lambda rows:rows[0].update(备注='replacement'))
        with patch('ingest.now',return_value='2026-11-14T15:05:00+08:00'):
            self.assertEqual(self.batch()['readiness'],'observing')

    @case('integration','sync.creation_blocker',('identity','writeback'))
    def test_unrelated_unidentified_row_does_not_block_all_new_models(self):
        self.config(lambda c:c['roles']['channels'].update(creation_guard_keys=['name']))
        self.edit_remote(lambda t:t['records'].append({'record_id':'legacy','fields':{'fld_name':'Unrelated model','fld_url':'','fld_publisher':'Other'}}))
        plan=self.make_plan()
        self.assertEqual(len(plan['operations']),2)
        self.assertTrue(all(op['kind']=='create' for op in plan['operations']))

    @case(target='sync.creation_blocker',tags=('identity','writeback'))
    def test_same_name_with_incomplete_identity_requires_adoption(self):
        self.config(lambda c:c['roles']['channels'].update(creation_guard_keys=['name']))
        self.edit_remote(lambda t:t['records'].append({'record_id':'legacy','fields':{'fld_name':'演示渠道 A','fld_url':'','fld_publisher':'Other'}}))
        plan=self.make_plan()
        self.assertTrue(any(x['reason']=='remote_name_or_alias_requires_adoption' for x in plan['issues']))
        self.assertEqual(len(plan['operations']),1)

    @case(target='sync.creation_blocker',tags=('identity','writeback'))
    def test_same_source_hidden_in_ambiguous_cell_blocks_duplicate_creation(self):
        self.config(lambda c:c['roles']['channels'].update(creation_guard_keys=['name']))
        self.edit_remote(lambda t:t['records'].append({'record_id':'legacy','fields':{'fld_name':'Old alias','fld_url':'https://example.org/a；https://example.org/other','fld_publisher':'Other'}}))
        plan=self.make_plan()
        self.assertTrue(any(x['reason']=='ambiguous_remote_source_requires_adoption' for x in plan['issues']))

    @case('integration','sync coalesce -> update readback',('writeback','batching'))
    def test_multiple_changed_fields_in_one_record_use_one_guarded_update(self):
        self.seed()
        self.edit_csv(lambda rows:rows[0].update(渠道名称='New name',备注='New note'))
        plan=self.make_plan()
        self.assertEqual(len(plan['operations']),1)
        self.assertEqual(set(plan['operations'][0]['fields']),{'name','note'})
        self.assertEqual(sync.apply(self.cfg,self.state,plan,self.backend)['counts'],{'verified':1})

    @case(target='identity.url_identity',tags=('identity','benchmark'))
    def test_explicit_repository_preference_resolves_source_plus_mirror(self):
        cell='https://github.com/owner/benchmark；镜像 https://huggingface.co/datasets/owner/benchmark'
        self.assertEqual(url_identity(cell,'github.com'),'https://github.com/owner/benchmark')

    @case('integration','research.run -> cached candidates apply despite unrelated Agent failure',('writeback','partial'))
    def test_agent_failure_does_not_discard_other_valid_write_candidates(self):
        from research import main
        self.config(lambda c:c.update(agent={'command':[sys.executable,'-c','import sys;sys.exit(2)']}))
        result=main(['run','--config',str(self.config_path),'--date','2026-11-13','--mode','apply'])
        self.assertEqual(result['counts'],{'verified':2})
        self.assertEqual(result['status'],'partial')
        self.assertTrue(any(issue['reason']=='research_failed' for issue in result['issues']))

    @case(target='sync.plan',tags=('identity','writeback'))
    def test_existing_entity_identity_cannot_be_renamed_by_an_ai_candidate(self):
        from evidence import import_candidates
        self.seed();batch=self.batch();eid=batch['items'][0]['entity_id']
        packet={'schema_version':1,'batch_id':batch['batch_id'],'evidence':[
          {'evidence_id':'source','url':'https://example.org/source','kind':'source_statement','excerpt':'Fixture.',
           'observed_at':'2026-11-14T00:00:00Z'}],
          'items':[{'entity_id':eid,'fields':{'publisher':{'value':'Another Publisher','evidence_ids':['source']}}}]}
        file=self.root/'candidate.json';write_json(file,packet)
        import_candidates(self.cfg,self.state,batch,file)
        plan=sync.plan(self.cfg,self.state,batch,self.backend)
        self.assertEqual(plan['operations'],[])
        self.assertTrue(any(x['reason']=='immutable_identity_changed' for x in plan['issues']))

    @case(target='sync.apply',tags=('integrity','writeback'))
    def test_rehashed_plan_cannot_change_value_without_matching_its_proposal(self):
        from common import digest
        plan=self.make_plan();op=plan['operations'][0]
        op['fields']['note']='not supported by this proposal'
        op['operation_id']='op_'+digest({k:v for k,v in op.items() if k!='operation_id'})[:32]
        plan['plan_id']='plan_'+digest({k:v for k,v in plan.items() if k not in ('plan_id','created_at')})[:32]
        report=sync.apply(self.cfg,self.state,plan,self.backend)
        self.assertEqual(report['counts'].get('conflict'),1)
        self.assertEqual(len(self.remote()['tables']['channels']['records']),1)
