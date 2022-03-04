from tardis.adapters.sites.fakesite import FakeSiteAdapter
from tardis.exceptions.tardisexceptions import TardisError
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.utilities.attributedict import AttributeDict

from ...utilities.utilities import MockedSimulator, run_async

from pydantic.error_wrappers import ValidationError

from datetime import datetime
from datetime import timedelta
from unittest.mock import patch
from unittest import TestCase


class TestFakeSiteAdapter(TestCase):
    mock_config_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch("tardis.interfaces.siteadapter.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()

    def setUp(self):
        self.config = self.mock_config.return_value
        self.config.TestSite = AttributeDict(
            MachineMetaData=self.machine_meta_data,
            MachineTypes=["test2large"],
            MachineTypeConfiguration=self.machine_type_configuration,
            api_response_delay=MockedSimulator(0),
            resource_boot_time=MockedSimulator(100),
        )

        self.adapter = FakeSiteAdapter(machine_type="test2large", site_name="TestSite")

    @property
    def machine_meta_data(self):
        return AttributeDict(test2large=AttributeDict(Cores=8, Memory=32, Disk=1000))

    @property
    def machine_type_configuration(self):
        return AttributeDict(test2large=AttributeDict(jdl="submit.jdl"))

    def test_configuration_validation(self):
        for variable in ("api_response_delay", "api_response_delay"):
            old_value = getattr(self.config.TestSite, variable)
            setattr(self.config.TestSite, variable, "DoesNotWork")
            with self.assertRaises(ValidationError):
                # noinspection PyStatementEffect
                FakeSiteAdapter(machine_type="test2large", site_name="TestSite")
            setattr(self.config.TestSite, variable, old_value)

    def test_deploy_resource(self):
        response = run_async(self.adapter.deploy_resource, AttributeDict())
        self.assertEqual(response.resource_status, ResourceStatus.Booting)
        self.assertFalse(response.created - datetime.now() > timedelta(seconds=1))
        self.assertFalse(response.updated - datetime.now() > timedelta(seconds=1))

    def test_machine_meta_data(self):
        self.assertEqual(
            self.adapter.machine_meta_data, self.machine_meta_data.test2large
        )

    def test_machine_type(self):
        self.assertEqual(self.adapter.machine_type, "test2large")

    def test_site_name(self):
        self.assertEqual(self.adapter.site_name, "TestSite")

    def test_resource_status(self):
        # test tardis restart, where resource_boot_time is not set
        response = run_async(
            self.adapter.resource_status,
            AttributeDict(
                created=datetime.now(),
                resource_status=ResourceStatus.Booting,
                drone_uuid="test-123",
            ),
        )
        self.assertEqual(response.resource_status, ResourceStatus.Booting)

        deploy_response = run_async(self.adapter.deploy_resource, AttributeDict())
        deploy_response.update(AttributeDict(drone_uuid="test-123"))
        response = run_async(self.adapter.resource_status, deploy_response)
        self.assertEqual(response.resource_status, ResourceStatus.Booting)

        past_timestamp = datetime.now() - timedelta(seconds=100)
        deploy_response.update(
            AttributeDict(created=past_timestamp, drone_uuid="test-123")
        )
        response = run_async(self.adapter.resource_status, deploy_response)
        self.assertEqual(response.resource_status, ResourceStatus.Running)

        # test stopped resources
        response.update(AttributeDict(drone_uuid="test-123"))
        response = run_async(self.adapter.stop_resource, response)
        self.assertEqual(response.resource_status, ResourceStatus.Stopped)

        # test terminated resources
        response.update(AttributeDict(drone_uuid="test-123"))
        response = run_async(self.adapter.terminate_resource, response)
        self.assertEqual(response.resource_status, ResourceStatus.Deleted)

    def test_stop_resource(self):
        deploy_response = run_async(self.adapter.deploy_resource, AttributeDict())
        deploy_response.update(AttributeDict(drone_uuid="test-123"))
        run_async(self.adapter.stop_resource, deploy_response)
        response = run_async(self.adapter.resource_status, deploy_response)
        self.assertEqual(response.resource_status, ResourceStatus.Stopped)

    def test_terminate_resource(self):
        deploy_response = run_async(self.adapter.deploy_resource, AttributeDict())
        deploy_response.update(AttributeDict(drone_uuid="test-123"))
        run_async(self.adapter.terminate_resource, deploy_response)
        response = run_async(self.adapter.resource_status, deploy_response)
        self.assertEqual(response.resource_status, ResourceStatus.Deleted)

    def test_exception_handling(self):
        def test_exception_handling(raise_it, catch_it):
            with self.assertRaises(catch_it):
                with self.adapter.handle_exceptions():
                    raise raise_it

        matrix = [(Exception, TardisError)]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)
