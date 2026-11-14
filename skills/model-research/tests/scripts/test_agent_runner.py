import sys

from support import Workspace, case
from common import ResearchError
from evidence import dossier_path, read_dossier
from state import State
import agent_runner


class AgentTests(Workspace):
    @case(target='agent_runner.execute', tags=('agent',))
    def test_unconfigured_agent_returns_request_without_claiming_research(self):
        result = agent_runner.execute(self.cfg, self.state, self.batch())
        self.assertEqual(result['status'], 'waiting_research')
        from pathlib import Path
        self.assertTrue(Path(result['request']).is_file())

    @case('integration', 'agent_runner.execute -> evidence.import_candidates', ('agent',))
    def test_external_process_reads_request_and_returns_validated_candidates(self):
        program = '''import json,sys
r=json.load(open(sys.argv[-1]))
print(json.dumps({'schema_version':1,'batch_id':r['batch_id'],
'evidence':[{'evidence_id':'fixture','url':'https://example.org/fixture',
'kind':'source_statement','excerpt':'Test fixture only.','observed_at':'2026-11-14T00:00:00Z'}],
'items':[{'entity_id':r['entities'][0]['entity_id'],'fields':{
'note':{'value':'fixture candidate','evidence_ids':['fixture']}}}]}))
'''
        self.config(lambda c: c.update(agent={'command': [sys.executable, '-c', program]}))
        batch = self.batch()
        result = agent_runner.execute(self.cfg, self.state, batch)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['remaining'], 1)
        meta, _ = read_dossier(dossier_path(self.state, batch['items'][0]['entity_id']))
        self.assertEqual(meta['controlled_fields']['note']['value'], 'fixture candidate')

    @case(target='agent_runner.execute', tags=('agent', 'privacy'))
    def test_failed_agent_does_not_echo_private_stderr(self):
        program = "import sys; sys.stderr.write('PRIVATE_TEST_TOKEN'); sys.exit(1)"
        self.config(lambda c: c.update(agent={'command': [sys.executable, '-c', program]}))
        with self.assertRaises(ResearchError) as ctx:
            agent_runner.execute(self.cfg, self.state, self.batch())
        self.assertNotIn('PRIVATE_TEST_TOKEN', str(ctx.exception))

    @case(target='agent_runner.execute', tags=('agent',))
    def test_success_exit_without_json_is_rejected(self):
        self.config(lambda c: c.update(agent={'command': [sys.executable, '-c', "print('not JSON')"]}))
        with self.assertRaisesRegex(ResearchError, 'JSON candidate'):
            agent_runner.execute(self.cfg, self.state, self.batch())

    @case(target='state.State.lock', tags=('concurrency',))
    def test_other_state_owner_is_rejected_until_lock_released(self):
        other = State(self.cfg['_state'])
        self.addCleanup(other.close)
        with self.state.lock():
            with self.assertRaisesRegex(ResearchError, 'another process'):
                with other.lock():
                    self.fail('second writer entered')
        with other.lock():
            pass
