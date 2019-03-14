from tests.utilities.utilities import run_async
from tardis.exceptions.executorexceptions import CommandExecutionFailure
from tardis.utilities.executors.shellexecutor import ShellExecutor

from unittest import TestCase

import yaml


class TestAsyncRunCommand(TestCase):
    def setUp(self):
        self.executor = ShellExecutor()

    def test_run_command(self):

        self.assertEqual(run_async(self.executor.run_command, 'exit 0').exit_code, 0)

        with self.assertRaises(CommandExecutionFailure) as cf:
            run_async(self.executor.run_command, 'exit 255')
        self.assertEqual(cf.exception.exit_code, 255)

        self.assertEqual(run_async(self.executor.run_command, 'echo "Test"').stdout, "Test")

        self.assertEqual(run_async(self.executor.run_command, 'echo "Test" >>/dev/stderr').stderr, "Test")

    def test_construction_by_yaml(self):
        executor = yaml.safe_load("""
                      !ShellExecutor
        """)
        self.assertEqual(run_async(executor.run_command, 'exit 0').exit_code, 0)

        with self.assertRaises(CommandExecutionFailure) as cf:
            run_async(self.executor.run_command, 'exit 255')
        self.assertEqual(cf.exception.exit_code, 255)

        self.assertEqual(run_async(executor.run_command, 'echo "Test"').stdout, "Test")

        self.assertEqual(run_async(executor.run_command, 'echo "Test" >>/dev/stderr').stderr, "Test")
