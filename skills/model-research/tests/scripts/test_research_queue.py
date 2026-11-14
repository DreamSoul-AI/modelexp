import sys
from support import Workspace, case
from common import ResearchError, read_json, write_json
from evidence import dossier_path, read_dossier
import agent_runner

PROGRAM = '''import json,sys
from pathlib import Path
r=json.load(open(sys.argv[-1]))
counter=Path(sys.argv[1]); counter.write_text(counter.read_text()+'1' if counter.exists() else '1')
evidence=[]; dossiers=[]
for item in r['entities']:
 eid=item['entity_id']; ref='src_'+eid
 evidence.append({'evidence_id':ref,'url':'https://example.org/fixture','kind':'source_statement',
 'excerpt':'A test-only source.','observed_at':'2026-11-14T00:00:00Z'})
 dossiers.append({'entity_id':eid,'status':'researched','expected_generated_sha256':r['dossiers'][eid]['generated_sha256'],
 'sections':[{'key':'summary','markdown':'Test source synthesis.','evidence_ids':[ref]}]})
print(json.dumps({'schema_version':1,'batch_id':r['batch_id'],'evidence':evidence,'items':[],'dossiers':dossiers}))
'''


class QueueTests(Workspace):
    def configure(self):
        self.program = self.root/'fixture_agent.py'
        self.program.write_text(PROGRAM)
        self.counter = self.root/'calls.txt'
        self.config(lambda c: c.update(agent={'command':[sys.executable,str(self.program),str(self.counter)],'max_entities_per_run':1}))

    @case('integration', 'agent_runner.execute -> dossier import -> job cache', ('queue', 'idempotency'))
    def test_bounded_runs_advance_queue_and_skip_already_researched_entities(self):
        self.configure()
        batch = self.batch()
        first = agent_runner.execute(self.cfg,self.state,batch)
        self.assertEqual((first['processed'],first['remaining']),(1,1))
        second = agent_runner.execute(self.cfg,self.state,batch)
        self.assertEqual((second['processed'],second['remaining']),(1,0))
        third = agent_runner.execute(self.cfg,self.state,batch)
        self.assertEqual((third['processed'],third['cache_reused']),(0,2))
        self.assertEqual(self.counter.read_text(),'11')

    @case('integration', 'agent_runner.work_id', ('queue', 'version'))
    def test_changed_input_researches_only_changed_entity(self):
        self.configure()
        batch = self.batch()
        agent_runner.execute(self.cfg,self.state,batch)
        agent_runner.execute(self.cfg,self.state,batch)
        self.edit_csv(lambda rows: rows[0].update(备注='changed source'))
        result = agent_runner.execute(self.cfg,self.state,self.batch())
        self.assertEqual(result['processed'],1)
        self.assertEqual(result['cache_reused'],1)
        self.assertEqual(self.counter.read_text(),'111')

    @case('integration', 'agent_runner.execute', ('queue', 'recovery'))
    def test_crash_after_markdown_write_is_reconciled_without_new_model_call(self):
        self.configure()
        batch = self.batch()
        agent_runner.execute(self.cfg,self.state,batch)
        for file in (self.root/'state/research/jobs').glob('*.json'):
            file.unlink()
        result = agent_runner.execute(self.cfg,self.state,batch)
        self.assertEqual(result['cache_reused'],1)
        self.assertEqual(self.counter.read_text(),'11')

    @case(target='agent_runner.execute', tags=('queue','recovery'))
    def test_failed_job_is_recorded_and_not_retried_immediately(self):
        self.configure()
        self.program.write_text("import sys; sys.exit(2)")
        with self.assertRaises(ResearchError):
            agent_runner.execute(self.cfg,self.state,self.batch())
        with self.assertRaises(ResearchError):
            agent_runner.execute(self.cfg,self.state,self.batch())
        result = agent_runner.execute(self.cfg,self.state,self.batch())
        self.assertEqual(result['remaining'],2)
        self.assertEqual(result['processed'],0)
        self.assertTrue(all(read_json(p)['attempts'] == 1 for p in (self.root/'state/research/jobs').glob('*.json')))

    @case('integration', 'agent_runner.execute', ('queue','recovery'))
    def test_deleted_dossier_is_rebuilt_instead_of_trusting_job_receipt(self):
        self.configure()
        batch=self.batch()
        agent_runner.execute(self.cfg,self.state,batch)
        agent_runner.execute(self.cfg,self.state,batch)
        dossier_path(self.state,batch['items'][0]['entity_id']).unlink()
        result=agent_runner.execute(self.cfg,self.state,self.batch())
        self.assertEqual(result['processed'],1)
        self.assertEqual(self.counter.read_text(),'111')
