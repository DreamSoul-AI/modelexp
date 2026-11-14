import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from support import SCRIPTS, case


class JourneyTests(unittest.TestCase):
    @case('e2e', 'research.py CLI -> local file backend -> SQLite and report', ('cli', 'idempotency'))
    def test_external_cli_repeat_run_has_zero_extra_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = SCRIPTS / 'research.py'
            def run(*args):
                r = subprocess.run([sys.executable, str(entry), *args], capture_output=True, text=True, timeout=20)
                self.assertEqual(r.returncode, 0, r.stderr)
                return json.loads(r.stdout)
            run('demo', '--directory', directory, '--date', '2026-11-13')
            result = run('run', '--config', str(root/'project.json'), '--date', '2026-11-13', '--mode', 'apply')
            self.assertEqual(result['counts'], {'verified': 2})
            second = run('run', '--config', str(root/'project.json'), '--date', '2026-11-13', '--mode', 'apply')
            self.assertEqual(second['results'], [])
            self.assertTrue((root/'state/runs'/ (result['run_id']+'.md')).exists())
