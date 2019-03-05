from ..utilities.utilities import run_async
from tardis.utilities.shellexecutor import ShellExecutor

from unittest import TestCase


class TestAsyncRunCommand(TestCase):
    def setUp(self):
        self.executor = ShellExecutor()

    def test_run_command(self):

        self.assertEqual(run_async(self.executor.run_command, 'exit 0').exit_code, 0)
        self.assertEqual(run_async(self.executor.run_command, 'exit 255').exit_code, 255)

        self.assertEqual(run_async(self.executor.run_command, 'echo "Test"').stdout, "Test")

        self.assertEqual(run_async(self.executor.run_command, 'echo "Test" >>/dev/stderr').stderr, "Test")
