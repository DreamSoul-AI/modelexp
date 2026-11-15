from unittest.mock import patch
from copy import deepcopy
from pathlib import Path
import json
import subprocess

from support import Workspace, case
from common import ResearchError, write_json, read_json
from score_policy import ability, exact_standardized, language_output, validate_observation
import score_calibration as calibration
import scores


class ScorePolicyTests(Workspace):
    @case(target='score_policy.language_output', tags=('scores', 'scope'))
    def test_only_language_output_is_a_candidate(self):
        self.assertTrue(language_output(['图像输入', '文本输出']))
        self.assertTrue(language_output(['文本输入', '文本+音频输出']))
        self.assertFalse(language_output(['文本输入', '向量输出']))
        self.assertFalse(language_output(['文本输入', '图像输出']))
        self.assertFalse(language_output(['文本输入', '分数输出']))

    @case(target='score_policy.ability', tags=('scores', 'scope'))
    def test_new_benchmarks_stay_inside_fixed_three_abilities(self):
        self.assertEqual(ability('LCB v9｜代码'), 'code')
        self.assertEqual(ability('Terminal 4｜Agent'), 'agent')
        self.assertEqual(ability('AIME 2027｜数学'), 'math')
        self.assertIsNone(ability('GPQA｜科学'))
        self.assertIsNone(ability('IFEval｜指令遵循'))
        self.assertIsNone(ability('标化｜LCB v6｜代码'))

    @case(target='score_policy.exact_standardized', tags=('scores', 'calibration'))
    def test_unknown_or_inconsistent_frozen_mapping_is_not_invented(self):
        self.assertEqual(exact_standardized(50, [[50, 30], [70, 90]]), 30)
        self.assertIsNone(exact_standardized(60, [[50, 30], [70, 90]]))
        self.assertIsNone(exact_standardized(50, [[50, 30], [50, 40]]))

    @case(target='score_policy.validate_observation', tags=('scores', 'evidence'))
    def test_scores_require_the_actual_quote_and_evaluation_context(self):
        source = {'s': {'excerpt': 'Exact model A: LCB v6 80.5 percent, no tools.'}}
        observation = {'field': 'LCB v6｜代码', 'value': 80.5, 'evidence_id': 's',
                       'quote': 'LCB v6 80.5 percent', 'benchmark_version': 'v6', 'configuration': 'no tools'}
        self.assertEqual(validate_observation(observation, {'LCB v6｜代码': 'f'}, source), 80.5)
        for bad in ({'value': 90}, {'quote': 'not actually read'}, {'configuration': ''}, {'field': 'GPQA｜科学'}):
            with self.assertRaises(ResearchError):
                validate_observation({**observation, **bad}, {'LCB v6｜代码': 'f'}, source)

    def configure_scores(self):
        c = read_json(self.config_path)
        role = c['roles'].pop('channels')
        role['identity'] = ['source_url', 'revision', 'name']
        role['fields'] = {}
        definitions = [('source_url', '获取地址', 'text'), ('revision', '版本', 'text'), ('name', '模型名称', 'text'),
                       ('modalities', '模态', 'select'), ('category', '用途类别', 'select'), ('evidence', '证据状态', 'select'),
                       ('screen', '筛选状态', 'select'), ('basis', '逐项评测依据', 'text'), ('checked', '核对日期', 'datetime'),
                       ('raw', 'LCB v6｜代码', 'number'), ('scaled', '标化｜LCB v6｜代码', 'number')]
        schema = []
        options = {'modalities': ['文本输入', '文本输出', '向量输出'], 'category': ['代码', '基座研究', '翻译专项'],
                   'evidence': ['已核对公开成绩', '已查原始来源未找到目标成绩'],
                   'screen': ['基座单列', '专项用途单列', '可按单项筛选', '证据不足']}
        for key, name, kind in definitions:
            role['fields'][key] = {'field_id': 'f_' + key, 'type': kind, 'policy': 'readonly' if key in ('source_url', 'revision', 'name', 'modalities') else 'ai', 'bootstrap_empty': True}
            schema.append({'id': 'f_' + key, 'name': name, 'type': kind})
            if kind == 'select':schema[-1].update(multiple=key == 'modalities', options=[{'name': x} for x in options[key]])
        role['fields']['source_url']['identity_url'] = True
        role.pop('input', None);role.pop('source_id_column', None);role['allow_create'] = False
        c.update(roles={'models': role}, allow_writes=True, allow_unconfirmed_input=True,
                 scores={'enabled': True, 'codex_state_dir': str(self.root / 'auth'), 'model': 'fixture', 'max_entities_per_run': 1})
        write_json(self.config_path, c);self.open()
        write_json(self.root / 'remote.json', {'tables': {'models': {'fields': schema, 'records': [
            {'record_id': 'r1', 'fields': {'f_source_url': 'https://example.org/model', 'f_revision': 'v1', 'f_name': 'Model', 'f_modalities': ['文本输出']}},
            {'record_id': 'r2', 'fields': {'f_source_url': 'https://example.org/embedding', 'f_revision': 'v1', 'f_name': 'Embedding', 'f_modalities': ['向量输出']}}]}}})

    def fixture(self, language=True, category='代码'):
        def collect(request):
            return [{'entity_id': request['entities'][0]['entity_id'], 'evidence_id': 's', 'url': 'https://example.org/model',
                     'kind': 'source_statement', 'excerpt': 'Model is a language model. LCB v6 80.5 percent.',
                     'observed_at': '2026-11-16T00:00:00Z'}], []
        packet = {'items': [{'record_id': 'r1', 'is_language_model': language, 'category': category,
                            'evidence_id': 's', 'classification_quote': 'Model is a language model.', 'reason': 'fixture',
                            'observations': [{'field': 'LCB v6｜代码', 'value': 80.5, 'evidence_id': 's', 'quote': 'LCB v6 80.5 percent',
                                              'benchmark_version': 'v6', 'configuration': 'no tools'}], 'new_benchmarks': []}]}
        return collect, subprocess.CompletedProcess([], 0, json.dumps(packet), '')

    @case('integration', 'scores -> sources -> model -> guarded apply -> readback', ('scores', 'writeback'))
    def test_classification_and_evidence_apply_but_uncalibrated_scores_stay_candidates(self):
        self.configure_scores();collect, response = self.fixture()
        with patch('scores.collect', side_effect=collect), patch('scores.score_quota.available', return_value=(True, {})), patch('scores.run_process', return_value=response):
            result = scores.execute(self.cfg, self.state, self.backend, '2026-11-16', 'apply')
        table = read_json(self.root / 'remote.json')['tables']['models']['records']
        self.assertEqual(table[0]['fields']['f_category'], ['代码'])
        self.assertNotIn('f_raw', table[0]['fields'])
        self.assertNotIn('f_category', table[1]['fields'])
        self.assertTrue(any(i['reason'] == 'needs_frozen_calibration' for i in result['issues']))

    @case('integration', 'scores -> quota pause', ('scores', 'quota'))
    def test_low_quota_stops_all_model_calls_and_writes(self):
        self.configure_scores()
        before = (self.root / 'remote.json').read_bytes()
        collect, _ = self.fixture()
        with patch('scores.collect', side_effect=collect), patch('scores.score_quota.available', return_value=(False, {'reason': 'quota_low'})), patch('scores.run_process') as model:
            result = scores.execute(self.cfg, self.state, self.backend, '2026-11-16', 'apply')
        model.assert_not_called()
        self.assertEqual(result['reason'], 'quota_low')
        self.assertEqual((self.root / 'remote.json').read_bytes(), before)

    @case('integration', 'scores -> non language response', ('scores', 'scope'))
    def test_non_language_evidence_cannot_replay_old_candidates(self):
        self.configure_scores();collect, response = self.fixture(language=False, category='不适用')
        before = (self.root / 'remote.json').read_bytes()
        with patch('scores.collect', side_effect=collect), patch('scores.score_quota.available', return_value=(True, {})), patch('scores.run_process', return_value=response):
            scores.execute(self.cfg, self.state, self.backend, '2026-11-16', 'apply')
        self.assertEqual((self.root / 'remote.json').read_bytes(), before)

    @case('integration', 'scores -> frozen calibration -> guarded repeat', ('scores', 'calibration'))
    def test_new_freeze_recalculates_samples_and_accepts_new_scores_without_moving_reference(self):
        self.configure_scores()
        c = read_json(self.config_path);c['scores']['reference_file'] = str(self.root / 'reference.json')
        write_json(self.config_path, c);self.open()
        remote = read_json(self.root / 'remote.json')
        remote['tables']['models']['records'][0]['fields'].update(f_raw=50, f_scaled=99, f_category=['代码'])
        write_json(self.root / 'remote.json', remote)
        frozen = calibration.freeze(self.cfg, self.state, self.backend, 'fixture-v3')
        self.assertEqual(frozen['sample_counts']['LCB v6｜代码'], 1)
        reference = (self.root / 'reference.json').read_bytes()
        document = calibration.plan(self.cfg, self.state, self.backend)
        applied = calibration.apply(self.cfg, self.state, self.backend, document['path'])
        self.assertEqual(applied['status'], 'completed')
        self.assertEqual(read_json(self.root / 'remote.json')['tables']['models']['records'][0]['fields']['f_scaled'], 50)
        self.assertEqual(calibration.apply(self.cfg, self.state, self.backend, document['path'])['results'][0]['status'], 'already_applied')
        self.assertEqual(calibration.percentile(75, [{'value':50}]), 100)
        self.assertEqual(calibration.percentile(25, [{'value':50}]), 0)
        self.assertEqual((self.root / 'reference.json').read_bytes(), reference)
        with self.assertRaises(ResearchError):calibration.freeze(self.cfg, self.state, self.backend, 'overwrite')

    @case('integration', 'calibration -> changed raw score', ('scores', 'conflict'))
    def test_calibration_preserves_concurrent_manual_raw_score_change(self):
        self.configure_scores()
        c=read_json(self.config_path);c['scores']['reference_file']=str(self.root/'reference.json')
        write_json(self.config_path,c);self.open()
        remote=read_json(self.root/'remote.json');remote['tables']['models']['records'][0]['fields'].update(f_raw=50,f_scaled=99,f_category=['代码'])
        write_json(self.root/'remote.json',remote)
        calibration.freeze(self.cfg,self.state,self.backend,'fixture-v3')
        document=calibration.plan(self.cfg,self.state,self.backend)
        remote['tables']['models']['records'][0]['fields']['f_raw']=60
        write_json(self.root/'remote.json',remote)
        applied=calibration.apply(self.cfg,self.state,self.backend,document['path'])
        self.assertEqual(applied['results'][0]['status'],'conflict')
        self.assertEqual(read_json(self.root/'remote.json')['tables']['models']['records'][0]['fields']['f_scaled'],99)

    @case('integration', 'scores -> special base exclusion', ('scores', 'scope'))
    def test_base_and_translation_do_not_receive_general_scores(self):
        self.configure_scores();collect,response=self.fixture(category='基座研究')
        with patch('scores.collect',side_effect=collect),patch('scores.score_quota.available',return_value=(True,{})),patch('scores.run_process',return_value=response):
            scores.execute(self.cfg,self.state,self.backend,'2026-11-16','apply')
        fields=read_json(self.root/'remote.json')['tables']['models']['records'][0]['fields']
        self.assertEqual(fields['f_screen'],['基座单列']);self.assertNotIn('f_raw',fields)

    @case('integration', 'scores -> checked receipt', ('scores', 'idempotence'))
    def test_repeat_with_unchanged_record_uses_no_model(self):
        self.configure_scores();collect,response=self.fixture()
        with patch('scores.collect',side_effect=collect),patch('scores.score_quota.available',return_value=(True,{})),patch('scores.run_process',return_value=response) as call:
            scores.execute(self.cfg,self.state,self.backend,'2026-11-16','apply')
            scores.execute(self.cfg,self.state,self.backend,'2026-11-16','apply')
        self.assertEqual(call.call_count,1)

    @case('integration', 'scores -> existing date normalization', ('scores','datetime'))
    def test_existing_business_date_does_not_create_false_concurrent_change(self):
        self.configure_scores();remote=read_json(self.root/'remote.json')
        remote['tables']['models']['records'][0]['fields']['f_checked']='2026-11-13'
        write_json(self.root/'remote.json',remote)
        collect,response=self.fixture()
        with patch('scores.collect',side_effect=collect),patch('scores.score_quota.available',return_value=(True,{})),patch('scores.run_process',return_value=response):
            result=scores.execute(self.cfg,self.state,self.backend,'2026-11-16','apply')
        self.assertFalse(any(i.get('field')=='checked' and i['reason']=='both_sides_changed' for i in result['issues']))
        self.assertNotEqual(read_json(self.root/'remote.json')['tables']['models']['records'][0]['fields']['f_checked'],'2026-11-13')

    @case('integration', 'scores -> unchanged daily source', ('scores','quota'))
    def test_daily_unchanged_sources_require_no_new_model_turn(self):
        self.configure_scores();collect,response=self.fixture()
        with patch('scores.collect',side_effect=collect),patch('scores.score_quota.available',return_value=(True,{})),patch('scores.run_process',return_value=response):
            scores.execute(self.cfg,self.state,self.backend,'2026-11-16','apply')
        path=self.state.root/'scores/receipts/r1.json';receipt=read_json(path);receipt['checked_at']='2026-11-13T00:00:00+00:00';write_json(path,receipt)
        with patch('scores.collect',side_effect=collect),patch('scores.run_process') as call:
            result=scores.execute(self.cfg,self.state,self.backend,'2026-11-17','apply')
        call.assert_not_called();self.assertEqual(result['reason'],'sources_unchanged')

    @case(target='scores.cached_response', tags=('scores','recovery'))
    def test_saved_successful_response_requires_identical_sources_and_model(self):
        root=self.root/'scores';run=root/'calls/first';run.mkdir(parents=True)
        request={'entities':[{'record_id':'r1'}],'evidence':[{'excerpt':'actual source','observed_at':'yesterday'}],'runtime':{'model':'fixture'}}
        packet={'items':[]}
        write_json(run/'request.json',request);write_json(run/'response.json',packet);write_json(run/'model-result.json',{'exit_code':0})
        changed=deepcopy(request);changed['evidence'][0]['observed_at']='today'
        self.assertEqual(scores.cached_response(root,changed,root/'calls/new')[0],packet)
        changed['evidence'][0]['excerpt']='changed source'
        self.assertIsNone(scores.cached_response(root,changed,root/'calls/new')[0])
        write_json(run/'failure.json',{'reason':'invalid evidence'})
        self.assertIsNone(scores.cached_response(root,request,root/'calls/new')[0])
