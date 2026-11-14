"""Persistent batch/identity/operation state and process-level single writer lock."""
from contextlib import contextmanager
import fcntl
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from common import ResearchError, canonical, now, write_json


class State:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.root / 'state.sqlite3', timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS batches(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS entities(id TEXT PRIMARY KEY, role TEXT, identity TEXT);
        CREATE TABLE IF NOT EXISTS aliases(role TEXT, alias TEXT, entity TEXT, PRIMARY KEY(role,alias));
        CREATE TABLE IF NOT EXISTS mappings(entity TEXT PRIMARY KEY, record_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS baselines(entity TEXT, field TEXT, value TEXT, PRIMARY KEY(entity,field));
        CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY, plan_id TEXT, status TEXT,
          record_id TEXT, detail TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, payload TEXT);
        CREATE TABLE IF NOT EXISTS input_observations(day TEXT PRIMARY KEY, signature TEXT,
          first_seen TEXT, last_seen TEXT, observations INTEGER);
        ''')
        if 'entity' not in {r[1] for r in self.db.execute('PRAGMA table_info(operations)')}:
            self.db.execute('ALTER TABLE operations ADD COLUMN entity TEXT')
        self.db.commit()

    @contextmanager
    def lock(self):
        with (self.root / 'writer.lock').open('a') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ResearchError('another process owns this state directory') from exc
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def save_batch(self, batch):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO batches VALUES (?,?)', (batch['batch_id'], canonical(batch)))
        batch = self.batch(batch['batch_id'])
        write_json(self.root / 'batches' / (batch['batch_id'] + '.json'), batch)

    def batch(self, batch_id):
        row = self.db.execute('SELECT payload FROM batches WHERE id=?', (batch_id,)).fetchone()
        if not row:
            raise ResearchError('unknown batch_id')
        return json.loads(row[0])

    def observe_inputs(self, business_date, signature, observed_at, min_seconds):
        row = self.db.execute('SELECT * FROM input_observations WHERE day=?', (business_date,)).fetchone()
        first = row['first_seen'] if row and row['signature'] == signature else observed_at
        count = row['observations'] + 1 if row and row['signature'] == signature else 1
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO input_observations VALUES (?,?,?,?,?)',
                            (business_date, signature, first, observed_at, count))
        elapsed = (datetime.fromisoformat(observed_at) - datetime.fromisoformat(first)).total_seconds()
        return count >= 2 and elapsed >= min_seconds

    def pending_plans(self):
        return [r[0] for r in self.db.execute(
            "SELECT DISTINCT plan_id FROM operations WHERE status IN ('submitting','submitted','unknown')")]

    def register(self, entity, role, identity, alias=None):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO entities VALUES (?,?,?)', (entity, role, canonical(identity)))
            if alias:
                old = self.db.execute('SELECT entity FROM aliases WHERE role=? AND alias=?', (role, alias)).fetchone()
                if old and old[0] != entity:
                    return 'source_id_reassigned'
                self.db.execute('INSERT OR IGNORE INTO aliases VALUES (?,?,?)', (role, alias, entity))
        return None

    def baseline(self, entity, field):
        row = self.db.execute('SELECT value FROM baselines WHERE entity=? AND field=?', (entity, field)).fetchone()
        return (row is not None, json.loads(row[0]) if row else None)

    def accept(self, entity, record_id, values):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO mappings VALUES (?,?)', (entity, record_id))
            for field, value in values.items():
                self.db.execute('INSERT OR REPLACE INTO baselines VALUES (?,?,?)', (entity, field, canonical(value)))

    def operation(self, op_id):
        row = self.db.execute('SELECT * FROM operations WHERE id=?', (op_id,)).fetchone()
        return dict(row) if row else None

    def pending(self, entity):
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM operations WHERE entity=? AND status IN ('submitting','submitted','unknown')", (entity,))]

    def mark(self, op_id, plan_id, status, record_id=None, detail=None, entity=None):
        previous = self.operation(op_id)
        if previous:
            record_id = record_id or previous['record_id']
            entity = entity or previous['entity']
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO operations VALUES (?,?,?,?,?,?,?)',
                            (op_id, plan_id, status, record_id, canonical(detail), now(), entity))

    def save_run(self, report):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO runs VALUES (?,?)', (report['run_id'], canonical(report)))
        write_json(self.root / 'runs' / (report['run_id'] + '.json'), report)

    def run(self, run_id):
        row = self.db.execute('SELECT payload FROM runs WHERE id=?', (run_id,)).fetchone()
        if not row:
            raise ResearchError('unknown run_id')
        return json.loads(row[0])

    def close(self):
        self.db.close()
