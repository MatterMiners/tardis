from ..utilities.utilities import run_async
from ..utilities.utilities import async_return
from tardis.agents.siteagent import SiteAgent
from tardis.interfaces.siteadapter import SiteAdapter

from unittest import TestCase
from unittest.mock import create_autospec
from unittest.mock import PropertyMock


class TestSiteAgent(TestCase):
    def setUp(self):
        self.site_adapter = create_autospec(SiteAdapter)
        self.site_agent = SiteAgent(self.site_adapter)

    def test_deploy_resource(self):
        self.site_adapter.deploy_resource.side_effect = async_return
        run_async(self.site_agent.deploy_resource, resource_attributes="test")
        self.site_adapter.deploy_resource.assert_called_with(resource_attributes='test')

    def test_dns_name(self):
        self.site_adapter.dns_name.return_value = None
        self.site_agent.dns_name(unique_id="test")
        self.site_adapter.dns_name.assert_called_with(unique_id='test')

    def test_handle_exceptions(self):
        self.site_adapter.handle_exceptions.return_value = None
        self.site_agent.handle_exceptions()
        self.site_adapter.handle_exceptions.assert_called_with()

    def test_handle_response(self):
        self.assertEqual(self.site_agent.handle_response("Test", {'test': 1}, {'test': 2}), NotImplemented)

    def test_machine_meta_data(self):
        type(self.site_adapter).machine_meta_data = PropertyMock(return_value="Test123")
        self.assertEqual(self.site_agent.machine_meta_data, "Test123")

    def test_machine_type(self):
        type(self.site_adapter).machine_type = PropertyMock(return_value="Test123")
        self.assertEqual(self.site_agent.machine_type, "Test123")

    def test_resource_status(self):
        self.site_adapter.resource_status.side_effect = async_return
        run_async(self.site_agent.resource_status, resource_attributes="test")
        self.site_adapter.resource_status.assert_called_with(resource_attributes='test')

    def test_site_name(self):
        type(self.site_adapter).site_name = PropertyMock(return_value="Test123")
        self.assertEqual(self.site_agent.site_name, "Test123")

    def test_stop_resource(self):
        self.site_adapter.stop_resource.side_effect = async_return
        run_async(self.site_agent.stop_resource, resource_attributes="test")
        self.site_adapter.stop_resource.assert_called_with(resource_attributes='test')

    def test_terminate_resource(self):
        self.site_adapter.terminate_resource.side_effect = async_return
        run_async(self.site_agent.terminate_resource, resource_attributes="test")
        self.site_adapter.terminate_resource.assert_called_with(resource_attributes='test')
