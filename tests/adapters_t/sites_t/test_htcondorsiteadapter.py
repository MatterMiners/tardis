from tardis.adapters.sites.htcondor import HTCondorSiteAdapter
from tardis.exceptions.tardisexceptions import TardisError
from tardis.utilities.attributedict import AttributeDict
from ...utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import patch


class TestHTCondorSiteAdapter(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapters.sites.htcondor.Configuration')
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_executor_patcher = patch('tardis.adapters.sites.htcondor.ShellExecutor')
        cls.mock_executor = cls.mock_executor_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_executor_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        test_site_config = config.TestSite
        test_site_config.MachineMetaData = self.machine_meta_data
        test_site_config.MachineTypeConfiguration = self.machine_type_configuration
        test_site_config.executor = self.mock_executor.return_value

        self.adapter = HTCondorSiteAdapter(machine_type='test2large', site_name='TestSite')

    @property
    def machine_meta_data(self):
        return AttributeDict(test2large=AttributeDict(Cores=8, Memory='32'))

    @property
    def machine_type_configuration(self):
        return AttributeDict(test2large=AttributeDict())

    def test_deploy_resource(self):
        run_async(self.adapter.deploy_resource, AttributeDict())

    def test_machine_meta_data(self):
        self.assertEqual(self.adapter.machine_meta_data, self.machine_meta_data.test2large)

    def test_machine_type(self):
        self.assertEqual(self.adapter.machine_type, 'test2large')

    def test_site_name(self):
        self.assertEqual(self.adapter.site_name, 'TestSite')

    def test_resource_status(self):
        run_async(self.adapter.resource_status, AttributeDict())

    def test_stop_resource(self):
        run_async(self.adapter.stop_resource, AttributeDict())

    def test_terminate_resource(self):
        run_async(self.adapter.terminate_resource, AttributeDict())

    def test_exception_handling(self):
        def test_exception_handling(to_raise, to_catch):
            with self.assertRaises(to_catch):
                with self.adapter.handle_exceptions():
                    raise to_raise

        matrix = [(Exception, TardisError)]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)
