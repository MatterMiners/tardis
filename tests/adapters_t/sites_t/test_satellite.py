from tardis.adapters.sites.satellite import SatelliteAdapter
from tardis.utilities.attributedict import AttributeDict
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed

from unittest import TestCase
from unittest.mock import AsyncMock, patch

import asyncio


class TestSatelliteAdapter(TestCase):
    mock_config_patcher = None
    mock_satelliteclient_patcher = None
    mock_sqliteregistry_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch("tardis.interfaces.siteadapter.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_satelliteclient_patcher = patch(
            "tardis.adapters.sites.satellite.SatelliteClient"
        )
        cls.mock_satelliteclient = cls.mock_satelliteclient_patcher.start()
        cls.mock_sqliteregistry_patcher = patch(
            "tardis.adapters.sites.satellite.SqliteRegistry"
        )
        cls.mock_sqliteregistry = cls.mock_sqliteregistry_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_satelliteclient_patcher.stop()
        cls.mock_sqliteregistry_patcher.stop()

    def setUp(self):

        self.remote_resource_uuid = "uuid-test"
        self.drone_uuid = "drone-test"

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

        self.registry = self.mock_sqliteregistry.return_value
        self.registry.async_get_resources = AsyncMock(return_value=[])
        self.registry.set_remote_resource_uuid = AsyncMock(return_value=True)

        self.mock_sqliteregistry.side_effect = None
        self.satellite_adapter = SatelliteAdapter(
            machine_type="testmachine_type", site_name="TestSite"
        )

    def tearDown(self):
        self.mock_satelliteclient.reset_mock()
        self.client.reset_mock()
        self.mock_sqliteregistry.reset_mock(side_effect=True)
        self.registry.reset_mock()

    def test_machine_type(self):
        self.assertEqual(self.satellite_adapter.machine_type, "testmachine_type")

    def test_site_name(self):
        self.assertEqual(self.satellite_adapter.site_name, "TestSite")

    def test_missing_sqliteregistry_configuration(self):
        with patch(
            "tardis.adapters.sites.satellite.SqliteRegistry",
            side_effect=AttributeError("Plugins.SqliteRegistry not configured"),
        ):
            with self.assertRaises(AttributeError):
                SatelliteAdapter(machine_type="testmachine_type", site_name="TestSite")

    def test_deploy_resource(self):
        resource_attributes = AttributeDict(drone_uuid=self.drone_uuid)

        with patch.object(
            self.satellite_adapter,
            "get_next_host",
            AsyncMock(return_value="uuid-new"),
        ) as mock_get_next_host:
            self.assertEqual(
                asyncio.run(
                    self.satellite_adapter.deploy_resource(
                        resource_attributes=resource_attributes,
                    )
                ),
                AttributeDict(remote_resource_uuid="uuid-new"),
            )

            mock_get_next_host.assert_awaited_once_with(resource_attributes)

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

    def test_get_next_host_claims_free_host(self):
        self.config.TestSite.machine_pool = ["machine-1"]
        self.client.get_status.return_value = {"power": {"state": "off"}}

        resource_attributes = AttributeDict(drone_uuid=self.drone_uuid)
        host = asyncio.run(
            self.satellite_adapter.get_next_host(
                resource_attributes=resource_attributes,
            )
        )

        self.assertEqual(host, "machine-1")
        self.registry.set_remote_resource_uuid.assert_awaited_once_with(
            self.drone_uuid, "machine-1", "TestSite"
        )

    def test_get_next_host_skips_occupied_host(self):
        self.config.TestSite.machine_pool = ["machine-1", "machine-2"]
        self.registry.async_get_resources.return_value = [
            {"remote_resource_uuid": "machine-1"}
        ]
        self.client.get_status.return_value = {"power": {"state": "off"}}

        resource_attributes = AttributeDict(drone_uuid=self.drone_uuid)
        host = asyncio.run(
            self.satellite_adapter.get_next_host(
                resource_attributes=resource_attributes,
            )
        )

        self.assertEqual(host, "machine-2")

    def test_get_next_host_skips_powered_on_host(self):
        self.config.TestSite.machine_pool = ["machine-1", "machine-2"]
        self.client.get_status = AsyncMock(
            side_effect=[
                {"power": {"state": "on"}},
                {"power": {"state": "off"}},
            ]
        )

        resource_attributes = AttributeDict(drone_uuid=self.drone_uuid)
        host = asyncio.run(
            self.satellite_adapter.get_next_host(
                resource_attributes=resource_attributes,
            )
        )

        self.assertEqual(host, "machine-2")

    def test_get_next_host_retries_after_claim_conflict(self):
        self.config.TestSite.machine_pool = ["machine-1", "machine-2"]
        self.client.get_status.return_value = {"power": {"state": "off"}}
        self.registry.set_remote_resource_uuid = AsyncMock(side_effect=[False, True])

        resource_attributes = AttributeDict(drone_uuid=self.drone_uuid)
        host = asyncio.run(
            self.satellite_adapter.get_next_host(
                resource_attributes=resource_attributes,
            )
        )

        self.assertEqual(host, "machine-2")

    def test_get_next_host_no_free_host(self):
        self.config.TestSite.machine_pool = ["machine-1"]
        self.client.get_status.return_value = {"power": {"state": "on"}}

        resource_attributes = AttributeDict(drone_uuid=self.drone_uuid)
        with self.assertRaises(TardisResourceStatusUpdateFailed):
            asyncio.run(
                self.satellite_adapter.get_next_host(
                    resource_attributes=resource_attributes,
                )
            )

    def _assert_resource_status(
        self,
        power_state,
        expected_status: ResourceStatus,
        previous_status: ResourceStatus = None,
        terminating: bool = False,
    ):
        """Exercise resource_status and assert the expected ResourceStatus mapping."""
        self.client.get_status.return_value = {"power": {"state": power_state}}

        resource_attributes = AttributeDict(
            remote_resource_uuid=self.remote_resource_uuid,
            resource_status=previous_status,
            satellite_terminating=terminating,
        )

        result = asyncio.run(
            self.satellite_adapter.resource_status(
                resource_attributes=resource_attributes,
            )
        )

        self.assertEqual(
            result,
            AttributeDict(
                remote_resource_uuid=self.remote_resource_uuid,
                resource_status=expected_status,
            ),
        )

        self.client.get_status.assert_awaited_once_with(self.remote_resource_uuid)

    def test_resource_status_running(self):
        self._assert_resource_status(
            "on", ResourceStatus.Running, previous_status=ResourceStatus.Stopped
        )

    def test_resource_status_running_from_booting(self):
        self._assert_resource_status(
            "on", ResourceStatus.Running, previous_status=ResourceStatus.Booting
        )

    def test_resource_status_booting(self):
        self._assert_resource_status(
            "off", ResourceStatus.Booting, previous_status=ResourceStatus.Booting
        )

    def test_resource_status_ambiguous_while_other_status(self):
        self._assert_resource_status(
            "na", ResourceStatus.Booting, previous_status=ResourceStatus.Booting
        )
        self.client.set_power.assert_not_awaited()

    def test_resource_status_deleted(self):
        self._assert_resource_status(
            "off",
            ResourceStatus.Deleted,
            previous_status=ResourceStatus.Stopped,
            terminating=True,
        )

    def test_resource_status_stopped(self):
        self._assert_resource_status(
            "off", ResourceStatus.Stopped, previous_status=ResourceStatus.Running
        )

    def test_resource_status_error(self):
        self._assert_resource_status(
            "suspended", ResourceStatus.Error, previous_status=None
        )

    def test_resource_status_forces_power_off_after_max_ambiguous_polls(self):
        self.config.TestSite.max_ambiguous_polls = 2
        self.client.get_status.return_value = {"power": {"state": "na"}}
        self.client.set_power = AsyncMock(return_value={})

        resource_attributes = AttributeDict(
            remote_resource_uuid=self.remote_resource_uuid,
            resource_status=ResourceStatus.Running,
        )

        for _ in range(2):
            result = asyncio.run(
                self.satellite_adapter.resource_status(
                    resource_attributes=resource_attributes,
                )
            )
            resource_attributes.update(result)
            self.client.set_power.assert_not_awaited()

        result = asyncio.run(
            self.satellite_adapter.resource_status(
                resource_attributes=resource_attributes,
            )
        )
        resource_attributes.update(result)

        self.client.set_power.assert_awaited_once_with("off", self.remote_resource_uuid)
        self.assertEqual(result.resource_status, ResourceStatus.Stopped)

    def test_resource_status_ambiguous_polls_reset_after_confirmed_reading(self):
        self.config.TestSite.max_ambiguous_polls = 2
        resource_attributes = AttributeDict(
            remote_resource_uuid=self.remote_resource_uuid,
            resource_status=ResourceStatus.Running,
        )

        self.client.get_status.return_value = {"power": {"state": "na"}}
        result = asyncio.run(
            self.satellite_adapter.resource_status(
                resource_attributes=resource_attributes,
            )
        )
        resource_attributes.update(result)
        self.assertEqual(resource_attributes["satellite_ambiguous_polls"], 1)

        self.client.get_status.return_value = {"power": {"state": "on"}}
        result = asyncio.run(
            self.satellite_adapter.resource_status(
                resource_attributes=resource_attributes,
            )
        )
        resource_attributes.update(result)
        self.assertEqual(resource_attributes["satellite_ambiguous_polls"], 0)

        self.client.get_status.return_value = {"power": {"state": "na"}}
        result = asyncio.run(
            self.satellite_adapter.resource_status(
                resource_attributes=resource_attributes,
            )
        )
        resource_attributes.update(result)
        self.assertEqual(resource_attributes["satellite_ambiguous_polls"], 1)
        self.client.set_power.assert_not_awaited()

    def test_stop_resource(self):
        self.client.set_power.return_value = {}

        resource_attributes = AttributeDict(
            remote_resource_uuid=self.remote_resource_uuid
        )
        result = asyncio.run(
            self.satellite_adapter.stop_resource(
                resource_attributes=resource_attributes,
            )
        )

        self.assertEqual(
            result,
            AttributeDict(
                remote_resource_uuid=self.remote_resource_uuid,
                resource_status=ResourceStatus.Stopped,
            ),
        )
        self.client.set_power.assert_awaited_once_with("off", self.remote_resource_uuid)

    def test_terminate_resource(self):
        resource_attributes = AttributeDict(
            remote_resource_uuid=self.remote_resource_uuid
        )
        asyncio.run(
            self.satellite_adapter.terminate_resource(
                resource_attributes=resource_attributes,
            )
        )

        self.assertTrue(resource_attributes["satellite_terminating"])
        self.client.set_power.assert_not_awaited()

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
