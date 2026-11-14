from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from support import case
from common import run_process


class ProcessTests(unittest.TestCase):
    @case(target='common.run_process',tags=('timeout','process'))
    def test_timeout_stops_model_process_and_its_child(self):
        with tempfile.TemporaryDirectory() as folder:
            marker=Path(folder)/'child-pid'
            program="import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)']);Path(sys.argv[1]).write_text(str(p.pid));time.sleep(10)"
            with self.assertRaises(subprocess.TimeoutExpired):
                run_process([sys.executable,'-c',program,str(marker)],timeout=0.5)
            self.assertTrue(marker.exists())
            status=Path('/proc')/marker.read_text()/'status'
            # Grandchildren receive SIGKILL asynchronously; observe a bounded exit window.
            deadline = time.monotonic() + 1
            stopped = False
            while time.monotonic() < deadline:
                try:
                    stopped = '\nState:\tZ' in '\n' + status.read_text()
                except FileNotFoundError:
                    stopped = True
                if stopped:
                    break
                time.sleep(0.01)
            self.assertTrue(stopped)
