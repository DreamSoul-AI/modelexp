import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from common import load_config, read_json, write_json
from research import demo
from state import State
from lark_adapter import FileAdapter
from ingest import ingest
from evidence import prepare_dossiers
import sync


def case(level='unit', target='', tags=()):
    def decorate(method):
        method.test_metadata = {'level': level, 'type': 'content', 'priority': 'p1',
                                'cost_class': 'c1', 'result_type': 'categorical',
                                'target': target, 'tags': list(tags)}
        return method
    return decorate


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        demo(self.root, '2026-11-13')
        self.config_path = self.root / 'project.json'
        self.open()

    def open(self):
        if hasattr(self, 'state'):
            self.state.close()
        self.cfg = load_config(self.config_path)
        self.state = State(self.cfg['_state'])
        self.backend = FileAdapter(self.cfg['backend']['path'])

    def tearDown(self):
        self.state.close()

    def config(self, change):
        cfg = read_json(self.config_path)
        change(cfg)
        write_json(self.config_path, cfg)
        self.open()

    def batch(self, manifest=None):
        value = ingest(self.cfg, self.state, '2026-11-13', manifest_path=manifest)
        prepare_dossiers(self.state, value)
        return value

    def make_plan(self):
        return sync.plan(self.cfg, self.state, self.batch(), self.backend)

    def seed(self):
        plan = self.make_plan()
        result = sync.apply(self.cfg, self.state, plan, self.backend)
        self.assertEqual(result['status'], 'completed')
        return plan

    def edit_csv(self, change):
        path = self.root / 'incoming/channels_2026-11-13.csv'
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            columns = reader.fieldnames
        change(rows)
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def remote(self):
        return read_json(self.root / 'remote.json')

    def edit_remote(self, change):
        data = self.remote()
        change(data['tables']['channels'])
        write_json(self.root / 'remote.json', data)
