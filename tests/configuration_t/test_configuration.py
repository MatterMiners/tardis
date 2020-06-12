from tardis.configuration.configuration import Configuration
from tardis.utilities.executors.sshexecutor import SSHExecutor
from tardis.utilities.attributedict import AttributeDict

from unittest import TestCase
import os
import yaml


class TestConfiguration(TestCase):
    def setUp(self):
        self.test_path = os.path.dirname(os.path.realpath(__file__))
        self.configuration1 = Configuration(
            os.path.join(self.test_path, "CloudStackAIO.yml")
        )
        self.configuration2 = Configuration()

    def test_configuration_instances(self):
        self.assertNotEqual(id(self.configuration1), id(self.configuration2))

    def test_shared_state(self):
        self.assertEqual(
            id(self.configuration1.CloudStackAIO), id(self.configuration2.CloudStackAIO)
        )

    def test_load_configuration(self):
        self.configuration1.load_config(os.path.join(self.test_path, "Sites.yml"))
        self.assertEqual(id(self.configuration1.Sites), id(self.configuration2.Sites))
        self.assertEqual(
            self.configuration1.Sites,
            [
                dict(name="EXOSCALE", adapter="CloudStack"),
                dict(name="SLURM", adapter="Slurm"),
            ],
        )
        self.assertEqual(
            self.configuration2.CloudStackAIO,
            {"api_key": "asdfghjkl", "api_secret": "qwertzuiop"},
        )

    def test_update_configuration(self):
        with open(os.path.join(self.test_path, "OpenStack.yml"), "r") as config_file:
            config_file_content = yaml.safe_load(config_file)
        self.configuration1 = Configuration(config_file_content)
        self.assertEqual(
            self.configuration1.OpenStack,
            AttributeDict(api_key="qwertzuiop", api_secret="katze123"),
        )

    def test_translate_config(self):
        b64_result = (
            b"I2Nsb3VkLWNvbmZpZwoKd3JpdGVfZmlsZXM6CiAgLSBwYXRoOiAvZXRjL2huc2NpY2xvdWQvc2l0ZS1pZC5jZmcKICAgIGNvbn",  # noqa: B950
            b"RlbnQ6IHwKICAgICAgRXhvc2NhbGUKICAgIHBlcm1pc3Npb25zOiAnMDY0NCcK",
        )
        self.configuration1.load_config(os.path.join(self.test_path, "Sites.yml"))
        self.assertEqual(
            self.configuration1.EXOSCALE.MachineTypeConfiguration.Micro.user_data,
            b"".join(b64_result),
        )

        executor = self.configuration1.SLURM.executor
        self.assertIsInstance(executor, SSHExecutor)
        self.assertEqual(
            executor._parameters,
            dict(
                host="somehost.de",
                username="someuser",
                client_keys=["where the private key is"],
            ),
        )

    def test_access_missing_attribute(self):
        with self.assertRaises(AttributeError):
            _ = self.configuration2.FooBar
