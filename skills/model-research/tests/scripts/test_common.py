from contextlib import suppress
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from support import case
from common import run_process


class ProcessTests(unittest.TestCase):
    @case(target='common.run_process',tags=('timeout','process'))
    def test_timeout_stops_model_process_and_its_child(self):
        child_program = (
            "import os, time\n"
            "print(os.getpid(), flush=True)\n"
            "time.sleep(30)\n"
        )
        parent_program = (
            "import subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, '-c', sys.argv[1]])\n"
            "time.sleep(30)\n"
        )
        communicate = subprocess.Popen.communicate
        child_pid = None

        def clean_up_group(pid):
            with suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGKILL)

        def communicate_after_child_is_ready(process, *, input, timeout):
            nonlocal child_pid
            self.assertEqual(os.getpgid(process.pid), process.pid)
            self.addCleanup(clean_up_group, process.pid)
            # Allow the fixture to start before measuring the command timeout.
            readable, _, _ = select.select([process.stdout], [], [], 5)
            self.assertTrue(readable, 'child did not report its PID within 5 seconds')
            pid = process.stdout.readline().strip()
            self.assertTrue(pid.isdecimal(), 'child exited without reporting its PID')
            child_pid = int(pid)
            self.assertEqual(os.getpgid(child_pid), process.pid)
            return communicate(process, input=input, timeout=timeout)

        with patch.object(subprocess.Popen, 'communicate', communicate_after_child_is_ready):
            with self.assertRaises(subprocess.TimeoutExpired):
                run_process([sys.executable, '-c', parent_program, child_program], timeout=0.5)

        self.assertIsNotNone(child_pid)
        status = Path('/proc') / str(child_pid) / 'status'
        # SIGKILL is delivered asynchronously to the grandchild.
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            try:
                if '\nState:\tZ' in status.read_text():
                    return
            except (FileNotFoundError, ProcessLookupError):
                return
            time.sleep(0.01)
        self.fail('child was still running after the command timed out')
