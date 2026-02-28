from tardis.adapters.sites.satellite import SatelliteAdapter
from tardis.utilities.attributedict import AttributeDict
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tests.utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import AsyncMock, call, patch


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

        self.remote_resource_uuid = "uuid-test"

        self.config = self.mock_config.return_value
        self.config.TestSite = AttributeDict(
            host="https://test.satelliteclient.local",
            username="TestUser",
            secret="test123",
            ca_file="/path/to/cert",
            machine_pool=["testmachine"],
            domain=".test.satelliteclient.local",
            MachineTypes=["testmachine_type"],
            max_age=5,
            proxy="http://proxy.local:3128",
            MachineMetaData=AttributeDict(
                testmachine_type=AttributeDict(Cores=4, Memory=8, Disk=100)
            ),
            MachineTypeConfiguration=AttributeDict(
                testmachine_type=AttributeDict(
                    instance_type="testmachine_type",
                )
            ),
        )

        self.client = self.mock_satelliteclient.return_value
        self.client.get_status = AsyncMock(
            return_value={"status": "running", "id": self.remote_resource_uuid}
        )

        self.client.set_power = AsyncMock(return_value=None)
        self.client.set_satellite_parameter = AsyncMock(return_value=None)

        self.satellite_adapter = SatelliteAdapter(
            machine_type="testmachine_type", site_name="TestSite"
        )
        self.satellite_adapter.get_next_host = AsyncMock(return_value="uuid-new")

    def tearDown(self):
        self.mock_satelliteclient.reset_mock()
        self.client.reset_mock()

    def test_machine_type(self):
        self.assertEqual(self.satellite_adapter.machine_type, "testmachine_type")

    def test_site_name(self):
        self.assertEqual(self.satellite_adapter.site_name, "TestSite")

    def test_deploy_resource(self):
        self.assertEqual(
            run_async(
                self.satellite_adapter.deploy_resource,
                resource_attributes=AttributeDict(drone_uuid="testsite-089123"),
            ),
            AttributeDict(remote_resource_uuid="uuid-new"),
        )

        self.satellite_adapter.get_next_host.assert_awaited_once()

        self.client.set_power.assert_awaited_once_with(
            state="on", remote_resource_uuid="uuid-new"
        )

    def test_client_initialization(self):
        self.mock_satelliteclient.assert_called_once_with(
            host="https://test.satelliteclient.local",
            username="TestUser",
            secret="test123",
            ca_file="/path/to/cert",
            machine_pool=["testmachine"],
            max_age=5,
            domain=".test.satelliteclient.local",
            proxy="http://proxy.local:3128",
        )

    def _assert_resource_status(self, response: dict, expected_status: ResourceStatus):
        """Exercise resource_status and assert the expected ResourceStatus mapping."""
        self.client.get_status.return_value = response

        resource_attributes = AttributeDict(
            remote_resource_uuid=self.remote_resource_uuid
        )

        result = run_async(
            self.satellite_adapter.resource_status,
            resource_attributes=resource_attributes,
        )

        self.assertEqual(
            result,
            AttributeDict(
                remote_resource_uuid=self.remote_resource_uuid,
                resource_status=expected_status,
            ),
        )

        self.client.get_status.assert_awaited_once_with(self.remote_resource_uuid)
        return self.client

    def test_resource_status_running(self):
        response = {
            "power": {"state": "on"},
            "parameters": {"tardis_reservation_state": "free"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Running)
        client.set_satellite_parameter.assert_not_awaited()

    def test_resource_status_running_clears_booting(self):
        response = {
            "power": {"state": "on"},
            "parameters": {"tardis_reservation_state": "booting"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Running)
        client.set_satellite_parameter.assert_awaited_once_with(
            self.remote_resource_uuid, "tardis_reservation_state", "active"
        )

    def test_resource_status_booting(self):
        response = {
            "power": {"state": "off"},
            "parameters": {"tardis_reservation_state": "booting"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Booting)
        client.set_satellite_parameter.assert_not_awaited()

    def test_resource_status_deleted(self):
        response = {
            "power": {"state": "off"},
            "parameters": {"tardis_reservation_state": "terminating"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Deleted)

        # Deleted resources should clear drone UUID and free reservation.
        client.set_satellite_parameter.assert_has_awaits(
            [
                call(self.remote_resource_uuid, "TardisDroneUuid", ""),
                call(self.remote_resource_uuid, "tardis_reservation_state", "free"),
            ]
        )
        self.assertEqual(client.set_satellite_parameter.await_count, 2)

    def test_resource_status_stopped(self):
        response = {
            "power": {"state": "off"},
            "parameters": {"tardis_reservation_state": "active"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Stopped)
        client.set_satellite_parameter.assert_not_awaited()

    def test_resource_status_error(self):
        response = {
            "power": {"state": "suspended"},
            "parameters": {"tardis_reservation_state": "free"},
        }
        client = self._assert_resource_status(response, ResourceStatus.Error)
        client.set_satellite_parameter.assert_not_awaited()

    def test_stop_resource(self):
        self.client.set_power.return_value = {}

        resource_attributes = AttributeDict(
            remote_resource_uuid=self.remote_resource_uuid
        )
        result = run_async(
            self.satellite_adapter.stop_resource,
            resource_attributes=resource_attributes,
        )

        self.assertEqual(
            result,
            AttributeDict(
                remote_resource_uuid=self.remote_resource_uuid,
                resource_status=ResourceStatus.Stopped,
            ),
        )
        self.client.set_power.assert_awaited_once_with("off", self.remote_resource_uuid)
        self.client.set_satellite_parameter.assert_not_awaited()

    def test_exception_handling(self):
        def test_exception_handling(to_raise, to_catch):
            with self.assertRaises(to_catch):
                with self.satellite_adapter.handle_exceptions():
                    raise to_raise

        matrix = [
            (
                TardisResourceStatusUpdateFailed("no free host available"),
                TardisResourceStatusUpdateFailed,
            ),
            (RuntimeError("unexpected satellite error"), RuntimeError),
        ]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)
