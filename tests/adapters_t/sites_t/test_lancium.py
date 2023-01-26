from tardis.adapters.sites.lancium import LanciumAdapter
from tardis.exceptions.tardisexceptions import (
    TardisResourceStatusUpdateFailed,
    TardisError,
)
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.utilities.attributedict import AttributeDict

from simple_rest_client.exceptions import AuthError

from ...utilities.utilities import run_async, set_awaitable_return_value

from datetime import datetime
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
                environment=[
                    AttributeDict(
                        variable="SITECONFIG_PATH", value="T1_DE_KIT/KIT-Lancium"
                    )
                ],
                resources=AttributeDict(node_exclusive=True),
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
        set_awaitable_return_value(
            self.mocked_lancium_api.jobs.show_jobs,
            {
                "jobs": [
                    {"id": 123, "status": "created", "name": "testsite-089123"},
                    {"id": 124, "status": "submitted", "name": "testsite-089124"},
                    {"id": 125, "status": "queued", "name": "testsite-089125"},
                    {"id": 126, "status": "ready", "name": "testsite-089126"},
                    {"id": 127, "status": "running", "name": "testsite-089127"},
                    {"id": 128, "status": "error", "name": "testsite-089128"},
                    {"id": 129, "status": "finished", "name": "testsite-089129"},
                    {"id": 130, "status": "delete pending", "name": "testsite-089130"},
                    {"id": 131, "status": "deleted", "name": "testsite-089131"},
                ]
            },
        )
        set_awaitable_return_value(self.mocked_lancium_api.jobs.terminate_job, {})
        set_awaitable_return_value(self.mocked_lancium_api.jobs.delete_job, {})

    def test_deploy_resource(self):
        def run_it():
            return run_async(
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

        self.assertEqual(
            AttributeDict(
                drone_uuid="testsite-089123",
                remote_resource_uuid=123,
                resource_status=ResourceStatus.Booting,
            ),
            run_it(),
        )

        self.assertDictEqual(
            {
                "name": "testsite-089123",
                "qos": "high",
                "image": "lancium/ubuntu",
                "command_line": "sleep 500",
                "max_run_time": 600,
                "resources": {
                    "node_exclusive": True,
                    "core_count": 8,
                    "memory": 20,
                    "scratch": 20,
                },
                "environment": [
                    {
                        "variable": "SITECONFIG_PATH",
                        "value": "T1_DE_KIT/KIT-Lancium",
                    },
                    {"variable": "TardisDroneCores", "value": "8"},
                    {"variable": "TardisDroneMemory", "value": "20"},
                    {"variable": "TardisDroneDisk", "value": "20"},
                    {"variable": "TardisDroneUuid", "value": "testsite-089123"},
                ],
            },
            self.mocked_lancium_api.jobs.create_job.call_args[1]["job"],
        )
        self.mocked_lancium_api.jobs.submit_job.assert_called_with(id=123)

        self.mocked_lancium_api.jobs.create_job.side_effect = AuthError(
            "operation=auth_error", {}
        )
        with self.assertRaises(AuthError):
            run_it()

    def test_machine_meta_data(self):
        self.assertEqual(
            self.adapter.machine_meta_data, AttributeDict(Cores=8, Memory=20, Disk=20)
        )

    def test_machine_type(self):
        self.assertEqual(self.adapter.machine_type, "test2large")

    def test_site_name(self):
        self.assertEqual(self.adapter.site_name, "TestSite")

    def test_resource_status(self):
        def run_it(job_id, created=datetime.now()):
            return run_async(
                self.adapter.resource_status,
                resource_attributes=AttributeDict(
                    remote_resource_uuid=job_id,
                    drone_uuid=f"testsite-089{job_id}",
                    created=created,
                ),
            )

        test_matrix = [
            (123, ResourceStatus.Booting),
            (124, ResourceStatus.Booting),
            (125, ResourceStatus.Booting),
            (126, ResourceStatus.Booting),
            (127, ResourceStatus.Running),
            (128, ResourceStatus.Error),
            (129, ResourceStatus.Stopped),
            (130, ResourceStatus.Stopped),
            (131, ResourceStatus.Deleted),
        ]
        for job_id, resource_status in test_matrix:
            # remote_resource_uuid is stored as VARCHAR(255) in the drone registry.
            # In case drones are restored after a shutdown of TARDIS, we need to ensure
            # that the resource_status function can also handle remote_resource_uuids
            # of type string.
            for translation in (str, int):
                response = {
                    key: value
                    for key, value in run_it(translation(job_id)).items()
                    if key not in ["created", "updated"]
                }
                self.assertEqual(
                    {
                        "remote_resource_uuid": job_id,
                        "drone_uuid": f"testsite-089{job_id}",
                        "resource_status": resource_status,
                    },
                    response,
                )

        # check that resource not in the show_job list and older than maxAge
        # have status deleted
        for translation in (str, int):
            response = {
                key: value
                for key, value in run_it(
                    translation(999), datetime.fromtimestamp(0)
                ).items()
                if key not in ["created", "updated"]
            }
            self.assertEqual(
                {
                    "remote_resource_uuid": 999,
                    "drone_uuid": "testsite-089999",
                    "resource_status": ResourceStatus.Deleted,
                },
                response,
            )

            # check that resources not in the show_job list and younger than maxAge
            # raise TardisResourceStatusUpdateFailed
            with self.assertRaises(TardisResourceStatusUpdateFailed):
                run_it(translation(999), datetime.now())

        self.mocked_lancium_api.jobs.show_jobs.assert_called_once()

    def test_resource_status_failed(self):
        self.mocked_lancium_api.jobs.show_jobs.side_effect = AuthError(
            "operation=auth_error", {}
        )
        with self.assertRaises(AuthError):
            run_async(
                self.adapter.resource_status,
                resource_attributes=AttributeDict(
                    remote_resource_uuid=123,
                    drone_uuid="testsite-089123",
                ),
            )

    def test_stop_resource(self):
        def run_it():
            return run_async(
                self.adapter.stop_resource,
                resource_attributes=AttributeDict(remote_resource_uuid=123),
            )

        run_it()

        self.mocked_lancium_api.jobs.terminate_job.assert_called_with(id=123)

        self.mocked_lancium_api.jobs.terminate_job.side_effect = AuthError(
            "operation=auth_error", {}
        )
        with self.assertRaises(AuthError):
            run_it()

    def test_terminate_resource(self):
        def run_it():
            return run_async(
                self.adapter.terminate_resource,
                resource_attributes=AttributeDict(remote_resource_uuid=123),
            )

        run_it()
        self.mocked_lancium_api.jobs.delete_job.assert_called_with(id=123)

        self.mocked_lancium_api.jobs.delete_job.side_effect = AuthError(
            "operation=auth_error", {}
        )
        with self.assertRaises(AuthError):
            run_it()

    def test_exception_handling(self):
        with self.assertRaises(TardisError):
            with self.adapter.handle_exceptions():
                raise AuthError("test", "test")
