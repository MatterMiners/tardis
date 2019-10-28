from tests.utilities.utilities import run_async
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.executors.sshexecutor import SSHExecutor
from tardis.exceptions.executorexceptions import CommandExecutionFailure

from asyncssh import ProcessError
from asyncssh.misc import ConnectionLost, DisconnectError

try:
    from contextlib import asynccontextmanager
except ImportError:
    from aiotools import async_ctx_manager as asynccontextmanager

from unittest import TestCase
from unittest.mock import patch

import yaml


def generate_connect(response, exception=None):
    @asynccontextmanager
    async def connect(*args, **kwargs):
        class Connection(object):
            async def run(self, *args, input, **kwargs):
                if exception:
                    raise exception
                self.stdout = input and input.decode()
                return self

            @property
            def exit_status(self):
                return response.exit_status

            @property
            def stderr(self):
                return response.stderr

        yield Connection()

    return connect


class TestSSHExecutor(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_asyncssh_patcher = patch(
            "tardis.utilities.executors.sshexecutor.asyncssh"
        )
        cls.mock_asyncssh = cls.mock_asyncssh_patcher.start()
        cls.mock_asyncssh.ProcessError = ProcessError
        cls.mock_asyncssh.misc.ConnectionLost = ConnectionLost
        cls.mock_asyncssh.misc.DisconnectError = DisconnectError

    @classmethod
    def tearDownClass(cls):
        cls.mock_asyncssh.stop()

    def setUp(self) -> None:
        self.response = AttributeDict(stderr="", exit_status=0)
        self.mock_asyncssh.connect.side_effect = generate_connect(self.response)
        self.mock_asyncssh.reset_mock()

    def test_run_command(self):
        executor = SSHExecutor(
            host="test_host", username="test", client_keys=["TestKey"]
        )
        self.assertIsNone(run_async(executor.run_command, command="Test").stdout)
        self.mock_asyncssh.connect.assert_called_with(
            host="test_host", username="test", client_keys=["TestKey"]
        )
        self.mock_asyncssh.reset_mock()

        executor = SSHExecutor(
            host="test_host", username="test", client_keys=("TestKey",)
        )
        self.assertIsNone(run_async(executor.run_command, command="Test").stdout)
        self.mock_asyncssh.connect.assert_called_with(
            host="test_host", username="test", client_keys=("TestKey",)
        )

        self.mock_asyncssh.reset_mock()

        executor = SSHExecutor(
            host="test_host", username="test", client_keys=("TestKey",)
        )
        self.assertEqual(
            run_async(executor.run_command, command="Test", stdin_input="Test").stdout,
            "Test",
        )
        self.mock_asyncssh.connect.assert_called_with(
            host="test_host", username="test", client_keys=("TestKey",)
        )

    def test_run_raises_process_error(self):
        test_exception = ProcessError(
            env="Test",
            command="Test",
            subsystem="Test",
            exit_status=1,
            exit_signal=None,
            returncode=1,
            stdout="TestError",
            stderr="TestError",
        )

        self.mock_asyncssh.connect.side_effect = generate_connect(
            self.response, exception=test_exception
        )

        executor = SSHExecutor(
            host="test_host", username="test", client_keys=("TestKey",)
        )

        with self.assertRaises(CommandExecutionFailure):
            run_async(executor.run_command, command="Test", stdin_input="Test")

    def test_run_raises_ssh_errors(self):
        test_exceptions = [
            ConnectionResetError,
            DisconnectError(reason="test_reason", code=255),
            ConnectionLost(reason="test_reason"),
            BrokenPipeError,
        ]

        for test_exception in test_exceptions:
            self.mock_asyncssh.connect.side_effect = generate_connect(
                self.response, exception=test_exception
            )

            executor = SSHExecutor(
                host="test_host", username="test", client_keys=("TestKey",)
            )

            with self.assertRaises(CommandExecutionFailure):
                run_async(executor.run_command, command="Test", stdin_input="Test")

    def test_construction_by_yaml(self):
        executor = yaml.safe_load(
            """
                   !SSHExecutor
                   host: test_host
                   username: test
                   client_keys:
                    - TestKey
                   """
        )
        response = AttributeDict(stderr="", exit_status=0)

        self.mock_asyncssh.connect.side_effect = generate_connect(response)
        self.assertEqual(
            run_async(executor.run_command, command="Test", stdin_input="Test").stdout,
            "Test",
        )
        self.mock_asyncssh.connect.assert_called_with(
            host="test_host", username="test", client_keys=["TestKey"]
        )
        self.mock_asyncssh.connect.side_effect = None
        self.mock_asyncssh.reset_mock()
