from tests.utilities.utilities import async_return, run_async
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.executors.sshexecutor import (
    SSHExecutor,
    probe_max_session,
    MFASSHClient,
    DupingSSHExecutor,
)
from tardis.exceptions.executorexceptions import CommandExecutionFailure
from tardis.exceptions.tardisexceptions import TardisAuthError

from asyncssh import ChannelOpenError, ConnectionLost, DisconnectError, ProcessError

from unittest import TestCase
from unittest.mock import patch

import asyncio
import yaml
import contextlib
import logging
from asyncstdlib import contextmanager as asynccontextmanager


DEFAULT_MAX_SESSIONS = 10


class MockConnection(object):
    def __init__(self, exception=None, __max_sessions=DEFAULT_MAX_SESSIONS, **kwargs):
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
            elif command == "lost_connection":
                return AttributeDict(stdout="", stderr="", exit_status=None)
            elif command not in ("Test", "/bin/bash", "test_wrapper"):
                raise ValueError(f"Unsupported mock command: {command}")
            return AttributeDict(
                stdout=f"command={command}, stdin={input}",
                stderr="TestError",
                exit_status=0,
            )

    async def create_process(self):
        @asynccontextmanager
        async def fake_process():
            with self._multiplex_session():
                yield

        return fake_process()


class TestSSHExecutorUtilities(TestCase):
    def test_max_sessions(self):
        with self.subTest(sessions="default"):
            self.assertEqual(
                DEFAULT_MAX_SESSIONS, run_async(probe_max_session, MockConnection())
            )
        for expected in (1, 9, 11, 20, 100):
            with self.subTest(sessions=expected):
                self.assertEqual(
                    expected,
                    run_async(probe_max_session, MockConnection(None, expected)),
                )


class TestMFASSHClient(TestCase):
    def setUp(self):
        mfa_config = [
            {
                "prompt": "Enter MFA token:",
                "totp": "EJL2DAWFOH7QPJ3D6I2DK2ARTBEJDBIB",
            },
            {
                "prompt": "Yet another token:",
                "totp": "D22246GDKKEDK7AAM77ZH5VRDRL7Z6W7",
            },
        ]
        self.mfa_ssh_client = MFASSHClient(mfa_config=mfa_config)

    def test_kbdint_auth_requested(self):
        self.assertEqual(run_async(self.mfa_ssh_client.kbdint_auth_requested), "")

    def test_kbdint_challenge_received(self):
        def test_responses(prompts, num_of_expected_responses):
            responses = run_async(
                self.mfa_ssh_client.kbdint_challenge_received,
                name="test",
                instructions="no",
                lang="en",
                prompts=prompts,
            )

            self.assertEqual(len(responses), num_of_expected_responses)
            for response in responses:
                self.assertTrue(response.isdigit())

        for prompts, num_of_expected_responses in (
            ([("Enter MFA token:", False)], 1),
            ([("Enter MFA token:", False), ("Yet another token: ", False)], 2),
            ([], 0),
        ):
            test_responses(
                prompts=prompts, num_of_expected_responses=num_of_expected_responses
            )

        prompts_to_fail = [("Enter MFA token:", False), ("Unknown token: ", False)]

        with self.assertRaises(TardisAuthError) as tae:
            with self.assertLogs(level=logging.ERROR):
                run_async(
                    self.mfa_ssh_client.kbdint_challenge_received,
                    name="test",
                    instructions="no",
                    lang="en",
                    prompts=prompts_to_fail,
                )
        self.assertIn(
            "Keyboard interactive authentication failed: Unexpected Prompt",
            str(tae.exception),
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

        self.assertIsNone(self.executor._connection_state)
        run_async(force_connection)
        self.assertIsInstance(
            self.executor._connection_state.connection, MockConnection
        )
        current_ssh_connection = self.executor._connection_state
        run_async(force_connection)
        # make sure the connection is not needlessly replaced
        self.assertEqual(self.executor._connection_state, current_ssh_connection)

    def test_connection_race(self):
        # see https://github.com/MatterMiners/tardis/issues/369
        waiter = asyncio.Event()

        async def mocked_probe_max_session(connection):
            await waiter.wait()
            return 10

        async def run_bounded_connection():
            async with self.executor.bounded_connection as connection:
                return connection

        async def run_race_condition():
            first_connection = asyncio.ensure_future(run_bounded_connection())
            await asyncio.sleep(0.1)  # give some time to hit the waiter
            self.assertIsNone(self.executor._connection_state)
            second_connection = asyncio.ensure_future(run_bounded_connection())
            await asyncio.sleep(0.1)  # give some time to schedule the second tasks
            waiter.set()
            # check that no new connection is established
            self.assertEqual(await first_connection, await second_connection)

        # monkey patch prob session
        with patch(
            "tardis.utilities.executors.sshexecutor.probe_max_session",
            mocked_probe_max_session,
        ):
            run_async(run_race_condition)

    def test_lock(self):
        self.assertIsInstance(self.executor.lock, asyncio.Lock)

    def test_connection_queueing(self):
        async def is_queued(n: int):
            """Check whether the n'th command runs is queued or immediately"""
            background = [
                asyncio.ensure_future(self.executor.run_command("sleep 5"))
                for _ in range(n - 1)
            ]
            # probe can only finish in time if it is not queued
            probe = asyncio.ensure_future(self.executor.run_command("sleep 0.01"))
            await asyncio.sleep(0.1)
            queued = not probe.done()
            for task in background + [probe]:
                task.cancel()
            return queued

        for sessions in (1, 8, 10, 12, 20):
            with self.subTest(sessions=sessions):
                self.assertEqual(
                    sessions > DEFAULT_MAX_SESSIONS,
                    run_async(is_queued, sessions),
                )

    def test_run_command(self):
        self.assertEqual(
            run_async(self.executor.run_command, command="Test").stdout,
            "command=Test, stdin=None",
        )
        self.mock_asyncssh.connect.assert_called_with(
            host="test_host", username="test", client_keys=["TestKey"]
        )
        self.mock_asyncssh.reset_mock()

        response = run_async(
            self.executor.run_command, command="Test", stdin_input="Test"
        )

        self.assertEqual(response.stdout, "command=Test, stdin=Test")

        self.assertEqual(response.stderr, "TestError")

        self.assertEqual(response.exit_code, 0)

        with self.assertRaises(CommandExecutionFailure) as cef:
            run_async(self.executor.run_command, command="lost_connection")
        self.assertEqual(
            cef.exception.message,
            "Could not run command lost_connection due to a connection loss!",
        )
        self.assertEqual(cef.exception.stderr, "SSH connection lost")
        self.assertEqual(cef.exception.exit_code, 255)

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
        def test_yaml_construction(test_executor, *args, **kwargs):
            self.assertEqual(
                run_async(
                    test_executor.run_command, command="Test", stdin_input="Test"
                ).stdout,
                "command=Test, stdin=Test",
            )
            self.mock_asyncssh.connect.assert_called_with(*args, **kwargs)

            self.mock_asyncssh.reset_mock()

        executor = yaml.safe_load(
            """
                   !SSHExecutor
                   host: test_host
                   username: test
                   client_keys:
                    - TestKey
                   """
        )

        test_yaml_construction(
            executor,
            host="test_host",
            username="test",
            client_keys=["TestKey"],
        )

        mfa_executor = yaml.safe_load(
            """
                   !SSHExecutor
                   host: test_host
                   username: test
                   client_keys:
                     - TestKey
                   mfa_config:
                     - prompt: 'Token: '
                       totp: 123TopSecret
                   """
        )

        test_yaml_construction(
            mfa_executor,
            host="test_host",
            username="test",
            client_keys=["TestKey"],
            client_factory=mfa_executor._parameters["client_factory"],
        )


class TestDupingSSHExecutor(TestCase):
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
        self.executor = DupingSSHExecutor(**self.test_asyncssh_params)
        self.mock_asyncssh.reset_mock()

    def test_run_command(self):
        def test_wrapper_and_response(wrapper, response):
            self.assertEqual(
                response.stdout, f"command={wrapper}, stdin=Test\nTestStdInput\n"
            )
            self.assertEqual(response.stderr, "TestError")
            self.assertEqual(response.exit_code, 0)

        response = run_async(
            self.executor.run_command, command="Test", stdin_input="TestStdInput"
        )

        test_wrapper_and_response(wrapper="/bin/bash", response=response)

        self.executor = DupingSSHExecutor(
            wrapper="test_wrapper", **self.test_asyncssh_params
        )

        response = run_async(
            self.executor.run_command, command="Test", stdin_input="TestStdInput"
        )

        test_wrapper_and_response(wrapper="test_wrapper", response=response)

    def test_construction_by_yaml(self):
        def test_yaml_construction(test_executor, wrapper, *args, **kwargs):
            command = "Test"
            self.assertEqual(
                run_async(
                    test_executor.run_command,
                    command=command,
                    stdin_input="TestStdInput",
                ).stdout,
                f"command={wrapper}, stdin={command}\nTestStdInput\n",
            )
            self.mock_asyncssh.connect.assert_called_with(*args, **kwargs)

            self.mock_asyncssh.reset_mock()

        executor_to_test = yaml.safe_load(
            """
        !DupingSSHExecutor
        host: test_host
        username: test
        client_keys:
          - TestKey
        """
        )

        test_yaml_construction(
            executor_to_test,
            "/bin/bash",
            host="test_host",
            username="test",
            client_keys=["TestKey"],
        )

        test_executor_w_wrapper = yaml.safe_load(
            """
        !DupingSSHExecutor
        host: test_host
        username: test
        client_keys:
          - TestKey
        wrapper: test_wrapper
        """
        )

        test_yaml_construction(
            test_executor_w_wrapper,
            "test_wrapper",
            host="test_host",
            username="test",
            client_keys=["TestKey"],
        )
