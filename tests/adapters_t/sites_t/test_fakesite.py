from tardis.adapters.sites.fakesite import FakeSiteAdapter
from tardis.utilities.attributedict import AttributeDict

from unittest.mock import patch
from unittest import TestCase


class TestFakeSiteAdapter(TestCase):
    mock_config_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapters.sites.fakesite.Configuration')
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        test_site_config = config.TestSite
        test_site_config.MachineMetaData = self.machine_meta_data
        test_site_config.MachineTypeConfiguration = self.machine_type_configuration

        self.adapter = FakeSiteAdapter(machine_type='test2large', site_name='TestSite')

    @property
    def machine_meta_data(self):
        return AttributeDict(test2large=AttributeDict(Cores=8, Memory=32))

    @property
    def machine_type_configuration(self):
        return AttributeDict(test2large=AttributeDict(jdl='submit.jdl'))

    def test_deploy_resource(self):
        ...

    def test_machine_meta_data(self):
        self.assertEqual(self.adapter.machine_meta_data, self.machine_meta_data.test2large)

    def test_machine_type(self):
        self.assertEqual(self.adapter.machine_type, 'test2large')

    def test_site_name(self):
        self.assertEqual(self.adapter.site_name, 'TestSite')

    def test_resource_status(self):
        ...

    def test_stop_resource(self):
        ...

    def test_terminate_resource(self):
        ...
