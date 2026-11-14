from unittest.mock import patch
from support import Workspace, case
from common import ResearchError
from codex_agent import candidate_packet, execute
from agent_runner import research_request


class CodexTests(Workspace):
    def example(self):
        batch=self.batch()
        item=batch['items'][0]
        eid=item['entity_id']
        request={'batch_id':batch['batch_id'],'entities':[item],
                 'dossiers':{eid:{'generated_sha256':None}}}
        evidence=[{'evidence_id':'source','entity_id':eid,'url':'https://example.org/release',
                   'excerpt':'Official source text.','kind':'source_statement','observed_at':'2026-11-14T00:00:00Z'}]
        response={'items':[{'entity_id':eid,'status':'researched',
                   'fields':[{'key':'note','value_json':'"documented"','evidence_ids':['source'],'context_json':'{}'}],
                   'sections':[{'key':'summary','markdown':'来源声明。','evidence_ids':['source']}]}]}
        return request,response,evidence

    @case(target='codex_agent.candidate_packet', tags=('codex','evidence'))
    def test_structured_codex_response_becomes_evidence_linked_candidate_and_markdown(self):
        request,response,evidence=self.example()
        packet=candidate_packet(request,response,evidence,[])
        self.assertEqual(packet['items'][0]['fields']['note']['value'],'documented')
        self.assertEqual(packet['dossiers'][0]['sections'][0]['markdown'],'来源声明。')

    @case(target='codex_agent.candidate_packet', tags=('codex','evidence'))
    def test_codex_cannot_attribute_another_entity_source_to_a_claim(self):
        request,response,evidence=self.example()
        response['items'][0]['fields'][0]['evidence_ids']=['unread_source']
        with self.assertRaisesRegex(ResearchError,'unrelated'):
            candidate_packet(request,response,evidence,[])

    @case(target='codex_agent.candidate_packet', tags=('codex','completeness'))
    def test_successful_model_must_account_for_every_entity_with_readable_sources(self):
        request,_,evidence=self.example()
        with self.assertRaisesRegex(ResearchError,'omitted'):
            candidate_packet(request,{'items':[]},evidence,[])

    @case(target='codex_agent.candidate_packet', tags=('codex','evidence'))
    def test_needs_review_report_does_not_publish_structured_fact_candidates(self):
        request,response,evidence=self.example()
        response['items'][0]['status']='needs_review'
        packet=candidate_packet(request,response,evidence,[])
        self.assertEqual(packet['items'][0]['fields'],{})

    @case('integration','codex_agent.execute -> source failures',('codex','unknown'))
    def test_unreadable_sources_create_unknown_report_without_calling_model(self):
        batch=self.batch()
        path=research_request(self.cfg,self.state,batch,[batch['items'][0]])
        with patch('codex_agent.collect',return_value=([],[{'entity_id':batch['items'][0]['entity_id'],'reason':'HTTP 404'}])), patch('codex_agent.run_process') as model:
            packet=execute(path)
        model.assert_not_called()
        self.assertEqual(packet['dossiers'][0]['status'],'unavailable')
        self.assertEqual(packet['evidence'],[])

    @case(target='codex_agent.candidate_packet',tags=('codex','format'))
    def test_repeated_section_paragraphs_are_preserved_under_one_section(self):
        request,response,evidence=self.example()
        response['items'][0]['sections'].append({'key':'summary','markdown':'第二段来源说明。','evidence_ids':['source']})
        packet=candidate_packet(request,response,evidence,[])
        sections=packet['dossiers'][0]['sections']
        self.assertEqual(len(sections),1)
        self.assertIn('来源声明。',sections[0]['markdown'])
        self.assertIn('第二段来源说明。',sections[0]['markdown'])
        self.assertEqual(sections[0]['evidence_ids'],['source'])
