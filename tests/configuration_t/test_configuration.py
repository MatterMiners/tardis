from tardis.configuration.configuration import Configuration

from unittest import TestCase
import os


class TestConfiguration(TestCase):
    def setUp(self):
        print(os.getcwd())
        self.test_path = os.path.dirname(os.path.realpath(__file__))
        self.configuration1 = Configuration(os.path.join(self.test_path, 'CloudStackAIO.yml'))
        self.configuration2 = Configuration()

    def test_configuration_instances(self):
        self.assertNotEqual(id(self.configuration1), id(self.configuration2))

    def test_shared_state(self):
        self.assertEqual(id(self.configuration1.CloudStackAIO), id(self.configuration2.CloudStackAIO))

    def test_load_configuration(self):
        self.configuration1.load_config(os.path.join(self.test_path, 'Sites.yml'))
        self.assertEqual(id(self.configuration1.Sites), id(self.configuration2.Sites))
        self.assertEqual(self.configuration1.Sites, ['Exoscale'])
        self.assertEqual(self.configuration2.CloudStackAIO, {'api_key': 'asdfghjkl', 'api_secret': 'qwertzuiop'})

    def test_base64_encoded_user_data(self):
        result = (b'I2Nsb3VkLWNvbmZpZwoKd3JpdGVfZmlsZXM6CiAgLSBwYXRoOiAvZXRjL2huc2NpY2xvdWQvc2l0ZS1pZC5jZmcKICAgIGNvbn',
                  b'RlbnQ6IHwKICAgICAgRXhvc2NhbGUKICAgIHBlcm1pc3Npb25zOiAnMDY0NCcK')
        self.configuration1.load_config(os.path.join(self.test_path, 'Sites.yml'))
        self.assertEqual(self.configuration1.Exoscale.MachineTypeConfiguration.Micro.user_data, b''.join(result))

    def test_access_missing_attribute(self):
        with self.assertRaises(AttributeError):
            _ = self.configuration2.FooBar
