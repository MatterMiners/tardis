from tests.utilities.utilities import run_async
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.executors.sshexecutor import SSHExecutor

try:
    from contextlib import asynccontextmanager
except ImportError:
    from aiotools import async_ctx_manager as asynccontextmanager

from unittest import TestCase
from unittest.mock import patch

import yaml


def generate_connect(response):
    @asynccontextmanager
    async def connect(*args, **kwargs):
        class Connection(object):
            async def run(self, *args, **kwargs):
                return self

            @property
            def exit_status(self):
                return response.exit_status

            @property
            def stdout(self):
                return response.stdout

            @property
            def stderr(self):
                return response.stderr
        yield Connection()
    return connect


class TestSSHExecutor(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_asyncssh_patcher = patch('tardis.utilities.executors.sshexecutor.asyncssh')
        cls.mock_asyncssh = cls.mock_asyncssh_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_asyncssh.stop()

    def test_run_command(self):
        response = AttributeDict(stdout="Test", stderr="", exit_status=0)
        executor = SSHExecutor(host="test_host", username="test", client_keys=["TestKey"])
        self.mock_asyncssh.connect.side_effect = generate_connect(response)
        self.assertEqual(run_async(executor.run_command, command="Test").stdout, "Test")
        self.mock_asyncssh.connect.assert_called_with(host="test_host", username="test",
                                                      client_keys=["TestKey"])
        self.mock_asyncssh.reset_mock()

        executor = SSHExecutor(host="test_host", username="test", client_keys=("TestKey",))
        self.assertEqual(run_async(executor.run_command, command="Test").stdout, "Test")
        self.mock_asyncssh.connect.assert_called_with(host="test_host", username="test",
                                                      client_keys=("TestKey",))
        self.mock_asyncssh.connect.side_effect = None
        self.mock_asyncssh.reset_mock()

    def test_construction_by_yaml(self):
        executor = yaml.safe_load("""
                   !SSHExecutor
                   host: test_host
                   username: test
                   client_keys:
                    - TestKey
                   """)
        response = AttributeDict(stdout="Test", stderr="", exit_status=0)

        self.mock_asyncssh.connect.side_effect = generate_connect(response)
        self.assertEqual(run_async(executor.run_command, command="Test").stdout, "Test")
        self.mock_asyncssh.connect.assert_called_with(host="test_host", username="test",
                                                      client_keys=["TestKey"])
        self.mock_asyncssh.connect.side_effect = None
        self.mock_asyncssh.reset_mock()
