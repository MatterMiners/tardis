from tardis.adapters.sites.satellite import SatelliteAdapter
from tardis.exceptions.tardisexceptions import TardisAuthError
from tardis.exceptions.tardisexceptions import TardisDroneCrashed
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.utilities.attributedict import AttributeDict
from tardis.interfaces.siteadapter import ResourceStatus
from tests.utilities.utilities import async_return, run_async

from aiohttp import ClientConnectionError
from aiohttp import ContentTypeError
from simple_rest_client.exceptions import AuthError
from simple_rest_client.exceptions import ClientError

from unittest import TestCase
from unittest.mock import patch, AsyncMock

import asyncio
import logging


class TestSatelliteAdapter(TestCase):
    mock_config_patcher = None
    mock_satelliteclient_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch("tardis.interfaces.siteadapter.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_satelliteclient_patcher = patch(
            "tardis.adapters.sites.satellite.SatelliteClient"
        )
        cls.mock_satelliteclient = cls.mock_satelliteclient_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_satelliteclient_patcher.stop()

    def setUp(self):
        self.config = self.mock_config.return_value
        self.config.TestSite = AttributeDict(
            site_name="https://test.satelliteclient.local",
            username="TestUser",
            token="test123",
            ssl_cert="/path/to/cert",
            machine_pool=["testmachine"],
            MachineTypes=["testmachine_type"],
            MachineMethaData=AttributeDict(
                testmachine_type=AttributeDict(Cores=4, Memory=8, Disk=100)
            ),
            MachineTypeConfiguration=AttributeDict(
                testmachine_type=AttributeDict(
                    instance_type="testmachine_type",
                )
            ),
        )

        client = self.mock_satelliteclient.return_value
        client.get_status.return_value = async_return(
            {"status": "running", "id": "srv-12345"}
        )
        # client.init_api.return_value = async_return(return_value=None)

        client.get_next_uuid = AsyncMock(return_value="uuid-123")
        client.set_power = AsyncMock(return_value=None)
        client.set_satellite_parameter = AsyncMock(return_value=None)

        self.satellite_adapter = SatelliteAdapter(
            machine_type="testmachine_type", site_name="TestSite"
        )

    def tearDown(self):
        self.mock_satelliteclient.reset_mock()

    def test_deploy_resource(self):
        self.assertEqual(
            run_async(
                self.satellite_adapter.deploy_resource,
                resource_attributes=AttributeDict(drone_uuid="testsite-089123"),
            ),
            AttributeDict(remote_resource_uuid="uuid-123"),
        )

        self.mock_satelliteclient.return_value.get_next_uuid.assert_called()

        self.mock_satelliteclient.return_value.set_power.assert_called_with(
            state="on", remote_resource_uuid="uuid-123"
        )

    def _assert_resource_status(self, response, expected_status: ResourceStatus):
        client = self.mock_satelliteclient.return_value
        client.get_status.reset_mock()
        client.set_satellite_parameter.reset_mock()
        client.get_status.return_value = async_return(return_value=response)

        resource_attributes = AttributeDict(remote_resource_uuid="srv-12345")

        result = run_async(
            self.satellite_adapter.resource_status,
            resource_attributes=resource_attributes,
        )

        self.assertEqual(
            result,
            AttributeDict(
                remote_resource_uuid="srv-12345",
                resource_status=expected_status,
            ),
        )

        client.get_status.assert_called_once_with("srv-12345")
        return client

    def test_resource_status_cases(self):

        # Running host and reserved=false.
        response = {
            "power": {"state": "on"},
            "parameters": {"tardis_reserved": "false"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Running)
        client.set_satellite_parameter.assert_not_awaited()

        # Terminating host -> reset reserved flag and as mark deleted.
        response = {
            "power": {"state": "off"},
            "parameters": {"tardis_reserved": "terminating"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Deleted)
        client.set_satellite_parameter.assert_awaited_once_with(
            "srv-12345", "tardis_reserved", "false"
        )

        # Reserved but host is offline
        response = {
            "power": {"state": "off"},
            "parameters": {"tardis_reserved": "true"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Stopped)
        client.set_satellite_parameter.assert_not_awaited()

        # unexpected power state
        response = {
            "power": {"state": "suspended"},
            "parameters": {"tardis_reserved": "false"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Error)
        client.set_satellite_parameter.assert_not_awaited()
