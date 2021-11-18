from tests.utilities.utilities import async_return, run_async
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.executors.sshexecutor import SSHExecutor, probe_max_session
from tardis.exceptions.executorexceptions import CommandExecutionFailure

from asyncssh import ChannelOpenError, ConnectionLost, DisconnectError, ProcessError

from unittest import TestCase
from unittest.mock import patch

import asyncio
import yaml
import contextlib
import asyncstdlib as a


class MockConnection(object):
    def __init__(self, exception=None, __max_sessions=10, **kwargs):
        self.exception = exception and exception(**kwargs)
        self.max_sessions = __max_sessions
        self.current_sessions = 0

    @contextlib.contextmanager
    def _multiplex_session(self):
        if self.current_sessions >= self.max_sessions:
            raise ChannelOpenError(code=2, reason="open failed")
        self.current_sessions += 1
        try:
            yield
        finally:
            self.current_sessions -= 1

    async def run(self, command, input=None, **kwargs):
        with self._multiplex_session():
            if self.exception:
                raise self.exception
            if command.startswith("sleep"):
                _, duration = command.split()
                await asyncio.sleep(float(duration))
            elif command != "Test":
                raise ValueError(f"Unsupported mock command: {command}")
            return AttributeDict(
                stdout=input and input.decode(), stderr="TestError", exit_status=0
            )

    async def create_process(self):
        @a.contextmanager
        async def fake_process():
            with self._multiplex_session():
                yield

        return fake_process()


class TestSSHExecutorUtilities(TestCase):
    def test_max_sessions(self):
        with self.subTest(sessions="default"):
            self.assertEqual(10, run_async(probe_max_session, MockConnection()))
        for expected in (1, 9, 11, 20, 100):
            with self.subTest(sessions=expected):
                self.assertEqual(
                    expected,
                    run_async(probe_max_session, MockConnection(None, expected)),
                )


class TestSSHExecutor(TestCase):
    mock_asyncssh = None

    @classmethod
    def setUpClass(cls):
        cls.mock_asyncssh_patcher = patch(
            "tardis.utilities.executors.sshexecutor.asyncssh"
        )
        cls.mock_asyncssh = cls.mock_asyncssh_patcher.start()
        cls.mock_asyncssh.ChannelOpenError = ChannelOpenError
        cls.mock_asyncssh.ConnectionLost = ConnectionLost
        cls.mock_asyncssh.DisconnectError = DisconnectError
        cls.mock_asyncssh.ProcessError = ProcessError

    @classmethod
    def tearDownClass(cls):
        cls.mock_asyncssh.stop()

    def setUp(self) -> None:
        self.response = AttributeDict(stderr="", exit_status=0)
        self.mock_asyncssh.connect.return_value = async_return(
            return_value=MockConnection()
        )
        self.test_asyncssh_params = AttributeDict(
            host="test_host", username="test", client_keys=["TestKey"]
        )
        self.executor = SSHExecutor(**self.test_asyncssh_params)
        self.mock_asyncssh.reset_mock()

    @patch("tardis.utilities.executors.sshexecutor.asyncio.sleep", async_return)
    def test_establish_connection(self):
        self.assertIsInstance(
            run_async(self.executor._establish_connection), MockConnection
        )

        self.mock_asyncssh.connect.assert_called_with(**self.test_asyncssh_params)

        test_exceptions = [
            ConnectionResetError(),
            DisconnectError(reason="test_reason", code=255),
            ConnectionLost(reason="test_reason"),
            BrokenPipeError(),
        ]

        for exception in test_exceptions:
            self.mock_asyncssh.reset_mock()
            self.mock_asyncssh.connect.side_effect = exception

            with self.assertRaises(type(exception)):
                run_async(self.executor._establish_connection)

            self.assertEqual(self.mock_asyncssh.connect.call_count, 10)

        self.mock_asyncssh.connect.side_effect = None

    def test_connection_property(self):
        async def force_connection():
            async with self.executor.bounded_connection as connection:
                return connection

        self.assertIsNone(self.executor._ssh_connection)
        run_async(force_connection)
        self.assertIsInstance(self.executor._ssh_connection, MockConnection)
        current_ssh_connection = self.executor._ssh_connection
        run_async(force_connection)
        # make sure the connection is not needlessly replaced
        self.assertEqual(self.executor._ssh_connection, current_ssh_connection)

    def test_lock(self):
        self.assertIsInstance(self.executor.lock, asyncio.Lock)

    def test_run_command(self):
        self.assertIsNone(run_async(self.executor.run_command, command="Test").stdout)
        self.mock_asyncssh.connect.assert_called_with(
            host="test_host", username="test", client_keys=["TestKey"]
        )
        self.mock_asyncssh.reset_mock()

        response = run_async(
            self.executor.run_command, command="Test", stdin_input="Test"
        )

        self.assertEqual(response.stdout, "Test")

        self.assertEqual(response.stderr, "TestError")

        self.assertEqual(response.exit_code, 0)

        raising_executor = SSHExecutor(**self.test_asyncssh_params)

        self.mock_asyncssh.connect.return_value = async_return(
            return_value=MockConnection(
                exception=ProcessError,
                env="Test",
                command="Test",
                subsystem="Test",
                exit_status=1,
                exit_signal=None,
                returncode=1,
                stdout="TestError",
                stderr="TestError",
            )
        )

        with self.assertRaises(CommandExecutionFailure):
            run_async(raising_executor.run_command, command="Test", stdin_input="Test")

        raising_executor = SSHExecutor(**self.test_asyncssh_params)

        self.mock_asyncssh.connect.return_value = async_return(
            return_value=MockConnection(
                exception=ChannelOpenError, reason="test_reason", code=255
            )
        )

        with self.assertRaises(CommandExecutionFailure):
            run_async(raising_executor.run_command, command="Test", stdin_input="Test")

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

        self.assertEqual(
            run_async(executor.run_command, command="Test", stdin_input="Test").stdout,
            "Test",
        )
        self.mock_asyncssh.connect.assert_called_with(
            host="test_host", username="test", client_keys=["TestKey"]
        )
