from tardis.adapters.sites.lancium import LanciumAdapter
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.utilities.attributedict import AttributeDict

from simple_rest_client.exceptions import AuthError

from ...utilities.utilities import run_async, set_awaitable_return_value

from unittest import TestCase
from unittest.mock import patch


class TestLanciumAdapter(TestCase):
    mock_config_patcher = None
    mock_lancium_api_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_config_patcher = patch("tardis.interfaces.siteadapter.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_lancium_api_patcher = patch(
            "tardis.adapters.sites.lancium.LanciumClient"
        )
        cls.mock_lancium_api = cls.mock_lancium_api_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_lancium_api_patcher.stop()

    def setUp(self) -> None:
        self.mock_configuration()
        self.mock_lancium_adapter()
        self.adapter = LanciumAdapter(machine_type="test2large", site_name="TestSite")

    def mock_configuration(self):
        config = self.mock_config.return_value
        test_site_config = config.TestSite
        test_site_config.api_url = "https://test.site.api"
        test_site_config.api_key = "top_secret_test"
        test_site_config.max_age = 1
        test_site_config.MachineTypeConfiguration = AttributeDict(
            test2large=AttributeDict(
                qos="high",
                image="lancium/ubuntu",
                command_line="sleep 500",
                max_run_time=600,
            )
        )
        test_site_config.MachineMetaData = AttributeDict(
            test2large=AttributeDict(Cores=8, Memory=20, Disk=20)
        )

    def mock_lancium_adapter(self):
        self.mocked_lancium_api = self.mock_lancium_api.return_value
        set_awaitable_return_value(
            self.mocked_lancium_api.jobs.create_job,
            {"job": {"id": 123, "status": "created", "name": "testsite-089123"}},
        )
        set_awaitable_return_value(self.mocked_lancium_api.jobs.submit_job, {})

    def test_deploy_resource(self):
        self.assertEqual(
            AttributeDict(
                drone_uuid="testsite-089123",
                remote_resource_uuid=123,
                resource_status=ResourceStatus.Booting,
            ),
            run_async(
                self.adapter.deploy_resource,
                resource_attributes=AttributeDict(
                    drone_uuid="testsite-089123",
                    obs_machine_meta_data_translation_mapping=AttributeDict(
                        Cores=1,
                        Memory=1,
                        Disk=1,
                    ),
                ),
            ),
        )

        self.assertDictEqual(
            {
                "name": "testsite-089123",
                "qos": "high",
                "image": "lancium/ubuntu",
                "command_line": "sleep 500",
                "max_run_time": 600,
                "resources": {"core_count": 8, "memory": 20, "scratch": 20},
                "environment": [
                    {"variable": "TardisDroneCores", "value": "8"},
                    {"variable": "TardisDroneMemory", "value": "20"},
                    {"variable": "TardisDroneDisk", "value": "20"},
                    {"variable": "TardisDroneUuid", "value": "testsite-089123"},
                ],
            },
            self.mocked_lancium_api.jobs.create_job.call_args.kwargs["job"],
        )
        self.mocked_lancium_api.jobs.submit_job.assert_called_with(id=123)

        self.mocked_lancium_api.jobs.create_job.side_effect = AuthError(
            "operation=auth_error", {}
        )
        with self.assertRaises(AuthError):
            run_async(
                self.adapter.deploy_resource,
                resource_attributes=AttributeDict(
                    drone_uuid="testsite-089123",
                    obs_machine_meta_data_translation_mapping=AttributeDict(
                        Cores=1,
                        Memory=1,
                        Disk=1,
                    ),
                ),
            )

    def test_machine_meta_data(self):
        ...

    def test_machine_type(self):
        ...

    def test_site_name(self):
        ...

    def test_resource_status(self):
        ...

    def test_stop_resource(self):
        ...

    def test_terminate_resource(self):
        ...

    def test_exception_handling(self):
        ...
