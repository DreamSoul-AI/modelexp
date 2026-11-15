import copy
from pathlib import Path
import sys
from unittest.mock import patch

from support import Workspace, case
from common import ResearchError, digest, load_config, read_json, write_json
from evidence import dossier_path, read_dossier
from research import main
from state import State
from test_research_queue import PROGRAM
import research_pipeline
import service


class IndependentResearchTests(Workspace):
    def configure(self):
        program = self.root / 'agent.py'
        program.write_text(PROGRAM)
        self.counter = self.root / 'model-calls.txt'
        cfg = read_json(self.config_path)
        cfg.update(state_dir='./md-state', allow_writes=False,
                   agent={'enabled': True, 'command': [sys.executable, str(program), str(self.counter)],
                          'roles': ['channels'], 'max_entities_per_run': 1, 'include_previous_batches': True})
        self.md_config = self.root / 'md-project.json'
        write_json(self.md_config, cfg)
        return load_config(self.md_config)

    @case('integration', 'independent research -> Markdown only', ('research', 'isolation'))
    def test_research_writes_substantive_markdown_without_sync_plan_or_online_writes(self):
        self.configure()
        before = self.remote()
        with patch('sync.plan', side_effect=AssertionError('must not plan table writes')), patch(
                'sync.apply', side_effect=AssertionError('must not apply table writes')):
            result = main(['research', '--config', str(self.md_config), '--date', '2026-11-13'])
        self.assertEqual(result['remote_writes'], 0)
        self.assertEqual(result['research']['processed'], 1)
        self.assertEqual(self.remote(), before)
        files = [p for p in (self.root / 'md-state/dossiers').glob('*.md') if p.name != 'README.md']
        bodies = [read_dossier(p)[1] for p in files]
        self.assertTrue(any('Test source synthesis.' in body for body in bodies))
        self.assertFalse((self.root / 'state/requests').exists())

    @case('integration', 'CSV lock versus independent research state', ('research', 'concurrency'))
    def test_csv_writer_lock_does_not_block_research_and_research_lock_does_not_block_csv(self):
        cfg = self.configure()
        with self.state.lock():
            result = main(['research', '--config', str(self.md_config), '--date', '2026-11-13'])
        self.assertEqual(result['research']['processed'], 1)
        md_state = State(cfg['_state'])
        try:
            with md_state.lock():
                csv = main(['run', '--config', str(self.config_path), '--date', '2026-11-13', '--mode', 'apply'])
            self.assertEqual(csv['counts'], {'verified': 2})
        finally:
            md_state.close()

    @case(target='research.main', tags=('research', 'policy'))
    def test_write_enabled_config_is_rejected_before_ingest_or_model_call(self):
        with patch('research.ingest', side_effect=AssertionError('must fail before ingest')):
            with self.assertRaisesRegex(ResearchError, 'allow_writes=false'):
                main(['research', '--config', str(self.config_path), '--date', '2026-11-13'])

    @case('integration', 'research queue repeat', ('research', 'cache'))
    def test_completed_input_is_reused_without_extra_model_calls(self):
        self.configure()
        main(['research', '--config', str(self.md_config), '--date', '2026-11-13'])
        main(['research', '--config', str(self.md_config), '--date', '2026-11-13'])
        result = main(['research', '--config', str(self.md_config), '--date', '2026-11-13'])
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['research']['processed'], 0)
        self.assertEqual(self.counter.read_text(), '11')

    @case(target='research_pipeline.workset', tags=('research', 'backlog'))
    def test_previous_days_are_retained_and_newer_same_entity_input_wins(self):
        cfg = self.configure()
        state = State(cfg['_state'])
        try:
            old = copy.deepcopy(self.batch())
            old.update(batch_id='batch_old', config_hash=cfg['_hash'])
            state.save_batch(old)
            current = copy.deepcopy(old)
            current.update(batch_id='batch_new', business_date='2026-11-14', received_at='2026-11-14T15:00:00+08:00')
            current['items'] = [copy.deepcopy(old['items'][0])]
            current['items'][0]['raw_fields']['note'] = 'Newer version'
            state.save_batch(current)
            work = research_pipeline.workset(cfg, state, current)
            self.assertEqual(len(work['items']), 2)
            self.assertEqual(work['items'][0]['raw_fields']['note'], 'Newer version')
            self.assertEqual(work['items'][0]['source_business_date'], '2026-11-14')
            self.assertEqual(work['items'][1]['source_business_date'], '2026-11-13')
            again = research_pipeline.workset(cfg, state, current)
            self.assertEqual(again['batch_id'], work['batch_id'])
        finally:
            state.close()

    @case(target='research_pipeline.workset', tags=('research', 'source'))
    def test_modified_retained_source_is_rejected_before_model_call(self):
        cfg = self.configure()
        state = State(cfg['_state'])
        try:
            batch = self.batch()
            batch['config_hash'] = cfg['_hash']
            Path(batch['sources'][0]['path']).write_text('tampered')
            with self.assertRaisesRegex(ResearchError, 'immutable batch source'):
                research_pipeline.workset(cfg, state, batch)
        finally:
            state.close()

    @case('integration', 'research mode service release', ('research', 'deployment'))
    def test_research_service_uses_research_command_and_never_changes_remote(self):
        self.configure()
        root = self.root / 'md-service'
        service.install(root, self.md_config, mode='research', at='12:00', retry_until='23:59', continue_after_minutes=1)
        before = self.remote()
        result = service.tick(root, '2026-11-13')
        self.assertEqual(result['mode'], 'research')
        self.assertEqual(result['result']['research']['processed'], 1)
        self.assertEqual(result['result']['remote_writes'], 0)
        self.assertEqual(self.remote(), before)

    @case(target='service.install', tags=('research', 'policy'))
    def test_research_deployment_requires_remote_writes_disabled(self):
        with self.assertRaisesRegex(ResearchError, 'allow_writes=false'):
            service.install(self.root / 'bad-service', self.config_path, mode='research')

    @case(target='service.tick', tags=('research', 'policy'))
    def test_research_service_rejects_later_permission_escalation(self):
        self.configure()
        root = self.root / 'md-service'
        service.install(root, self.md_config, mode='research')
        cfg = read_json(self.md_config)
        cfg['allow_writes'] = True
        write_json(self.md_config, cfg)
        with self.assertRaisesRegex(ResearchError, 'write-enabled'):
            service.tick(root, '2026-11-13')
