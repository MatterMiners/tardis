from tardis.adapters.sites.slurm import SlurmAdapter
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.exceptions.executorexceptions import CommandExecutionFailure
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.utilities.attributedict import AttributeDict
from ...utilities.utilities import mock_executor_run_command
from ...utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import MagicMock, patch

from datetime import datetime, timedelta
from warnings import filterwarnings

import asyncio
import logging

__all__ = ["TestSlurmAdapter"]

TEST_RESOURCE_STATUS_RESPONSE = """
1390065||PENDING
1391999|fh2n1573|TIMEOUT
1391999.batch|fh2n1573|CANCELLED
"""

TEST_RESOURCE_STATUS_RESPONSE_RUNNING = """
1390065|fh2n1552|RUNNING
1390065.batch|fh2n1552|RUNNING
1391999|fh2n1573|TIMEOUT
1391999.batch|fh2n1573|CANCELLED
"""

TEST_RESOURCE_STATUS_RESPONSE_ALL_STATES = """
1000000|fh1n1000|BOOT_FAIL
1001000|fh1n1001|CANCELLED
1002000|fh1n1002|COMPLETED
1003000|fh1n1003|CONFIGURING
1004000|fh1n1004|COMPLETING
1005000|fh1n1005|DEADLINE
1006000|fh1n1006|FAILED
1007000|fh1n1007|NODE_FAIL
1008000|fh1n1008|OUT_OF_MEMORY
1009000||PENDING
1010000|fh1n1010|PREEMPTED
1011000|fh1n1011|RUNNING
1012000|fh1n1012|RESV_DEL_HOLD
1013000|fh1n1013|REQUEUE_FED
1014000|fh1n1014|REQUEUE_HOLD
1015000|fh1n1015|REQUEUED
1016000|fh1n1016|RESIZING
1017000|fh1n1017|REVOKED
1018000|fh1n1018|SIGNALING
1019000|fh1n1019|SPECIAL_EXIT
1020000|fh1n1020|STAGE_OUT
1021000|fh1n1021|STOPPED
1022000|fh1n1022|SUSPENDED
1023000|fh1n1023|TIMEOUT
"""

TEST_DEPLOY_RESOURCE_RESPONSE = """
Submitted batch job 1390065
"""


class TestSlurmAdapter(TestCase):
    mock_config_patcher = None
    mock_executor_patcher = None

    def check_attribute_dicts(
        self, expected_attributes, returned_attributes, exclude=tuple()
    ):
        for key in expected_attributes.keys():
            if key not in exclude:
                self.assertEqual(
                    getattr(returned_attributes, key), getattr(expected_attributes, key)
                )

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch("tardis.interfaces.siteadapter.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_executor_patcher = patch("tardis.adapters.sites.slurm.ShellExecutor")
        cls.mock_executor = cls.mock_executor_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_executor_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        config.TestSite = MagicMock(
            spec=[
                "MachineMetaData",
                "StatusUpdate",
                "MachineTypeConfiguration",
                "executor",
            ]
        )
        self.test_site_config = config.TestSite
        self.test_site_config.MachineMetaData = self.machine_meta_data
        self.test_site_config.StatusUpdate = 10
        self.test_site_config.MachineTypeConfiguration = self.machine_type_configuration
        self.test_site_config.executor = self.mock_executor.return_value

        self.slurm_adapter = SlurmAdapter(
            machine_type="test2large", site_name="TestSite"
        )

    def tearDown(self):
        pass

    @property
    def machine_meta_data(self):
        return AttributeDict(test2large=AttributeDict(Cores=20, Memory=62, Disk=100))

    @property
    def machine_type_configuration(self):
        return AttributeDict(
            test2large=AttributeDict(
                Partition="normal", StartupCommand="pilot.sh", Walltime="60"
            )
        )

    @property
    def resource_attributes(self):
        return AttributeDict(
            machine_type="test2large",
            site_name="TestSite",
            remote_resource_uuid=1390065,
            resource_status=ResourceStatus.Booting,
            drone_uuid="testsite-1390065",
        )

    def test_start_up_command_deprecation_warning(self):
        # Necessary to avoid annoying message in PyCharm
        filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)
        del self.test_site_config.MachineTypeConfiguration.test2large.StartupCommand

        with self.assertRaises(AttributeError):
            self.slurm_adapter = SlurmAdapter(
                machine_type="test2large", site_name="TestSite"
            )

        self.test_site_config.StartupCommand = "pilot.sh"

        with self.assertWarns(DeprecationWarning):
            self.slurm_adapter = SlurmAdapter(
                machine_type="test2large", site_name="TestSite"
            )

    @mock_executor_run_command(TEST_DEPLOY_RESOURCE_RESPONSE)
    def test_deploy_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(
            created=datetime.now(), updated=datetime.now()
        )

        resource_attributes = AttributeDict(
            machine_type="test2large",
            site_name="TestSite",
            obs_machine_meta_data_translation_mapping=AttributeDict(
                Cores=1,
                Memory=1024,
                Disk=1024,
            ),
            drone_uuid="testsite-1390065",
        )

        returned_resource_attributes = run_async(
            self.slurm_adapter.deploy_resource, resource_attributes
        )

        self.assertLess(
            returned_resource_attributes.created - expected_resource_attributes.created,
            timedelta(seconds=1),
        )

        self.check_attribute_dicts(
            expected_resource_attributes,
            returned_resource_attributes,
            exclude=("created", "updated"),
        )

        self.mock_executor.return_value.run_command.assert_called_with(
            "sbatch -p normal -N 1 -n 20 -t 60 --mem=63488mb --export=SLURM_Walltime=60,TardisDroneCores=20,TardisDroneMemory=63488,TardisDroneDisk=102400,TardisDroneUuid=testsite-1390065 pilot.sh"  # noqa: B950
        )

        self.mock_executor.reset_mock()

        self.test_site_config.MachineMetaData.test2large.Memory = 2.5

        run_async(self.slurm_adapter.deploy_resource, resource_attributes)

        self.mock_executor.return_value.run_command.assert_called_with(
            "sbatch -p normal -N 1 -n 20 -t 60 --mem=2560mb --export=SLURM_Walltime=60,TardisDroneCores=20,TardisDroneMemory=2560,TardisDroneDisk=102400,TardisDroneUuid=testsite-1390065 pilot.sh"  # noqa: B950
        )

        self.mock_executor.reset_mock()

        self.test_site_config.MachineMetaData.test2large.Memory = 2.546372129

        run_async(self.slurm_adapter.deploy_resource, resource_attributes)

        self.mock_executor.return_value.run_command.assert_called_with(
            "sbatch -p normal -N 1 -n 20 -t 60 --mem=2607mb --export=SLURM_Walltime=60,TardisDroneCores=20,TardisDroneMemory=2607,TardisDroneDisk=102400,TardisDroneUuid=testsite-1390065 pilot.sh"  # noqa: B950
        )

    @mock_executor_run_command(TEST_DEPLOY_RESOURCE_RESPONSE)
    def test_deploy_resource_w_submit_options(self):
        self.test_site_config.MachineTypeConfiguration.test2large.SubmitOptions = (
            AttributeDict(long=AttributeDict(gres="tmp:1G"))
        )

        slurm_adapter = SlurmAdapter(machine_type="test2large", site_name="TestSite")

        run_async(
            slurm_adapter.deploy_resource,
            resource_attributes=AttributeDict(
                machine_type="test2large",
                site_name="TestSite",
                obs_machine_meta_data_translation_mapping=AttributeDict(
                    Cores=1,
                    Memory=1000,
                    Disk=1000,
                ),
                drone_uuid="testsite-1390065",
            ),
        )

        self.mock_executor.return_value.run_command.assert_called_with(
            "sbatch -p normal -N 1 -n 20 -t 60 --gres=tmp:1G --mem=63488mb --export=SLURM_Walltime=60,TardisDroneCores=20,TardisDroneMemory=62000,TardisDroneDisk=100000,TardisDroneUuid=testsite-1390065 pilot.sh"  # noqa: B950
        )

    def test_machine_meta_data(self):
        self.assertEqual(
            self.slurm_adapter.machine_meta_data, self.machine_meta_data["test2large"]
        )

    def test_machine_type(self):
        self.assertEqual(self.slurm_adapter.machine_type, "test2large")

    def test_site_name(self):
        self.assertEqual(self.slurm_adapter.site_name, "TestSite")

    @mock_executor_run_command(TEST_RESOURCE_STATUS_RESPONSE)
    def test_resource_status(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now())

        returned_resource_attributes = run_async(
            self.slurm_adapter.resource_status,
            resource_attributes=self.resource_attributes,
        )

        self.assertLess(
            (
                returned_resource_attributes.updated
                - expected_resource_attributes.updated
            ),
            timedelta(seconds=1),
        )

        self.check_attribute_dicts(
            expected_resource_attributes,
            returned_resource_attributes,
            exclude=("created", "updated"),
        )

        self.mock_executor.return_value.run_command.assert_called_with(
            'squeue -o "%A|%N|%T" -h -t all'
        )

    @mock_executor_run_command(TEST_RESOURCE_STATUS_RESPONSE_RUNNING)
    def test_update_resource_status(self):
        self.assertEqual(
            self.resource_attributes["resource_status"], ResourceStatus.Booting
        )

        return_resource_attributes = run_async(
            self.slurm_adapter.resource_status,
            resource_attributes=self.resource_attributes,
        )

        self.assertEqual(
            return_resource_attributes["resource_status"], ResourceStatus.Running
        )

        self.assertEqual(
            return_resource_attributes["drone_uuid"],
            self.resource_attributes["drone_uuid"],
        )

        self.mock_executor.return_value.run_command.assert_called_with(
            'squeue -o "%A|%N|%T" -h -t all'
        )

    @mock_executor_run_command(TEST_RESOURCE_STATUS_RESPONSE_ALL_STATES)
    def test_resource_state_translation(self):
        state_translations = {
            "BOOT_FAIL": ResourceStatus.Error,
            "CANCELLED": ResourceStatus.Deleted,
            "COMPLETED": ResourceStatus.Deleted,
            "CONFIGURING": ResourceStatus.Booting,
            "COMPLETING": ResourceStatus.Running,
            "DEADLINE": ResourceStatus.Error,
            "FAILED": ResourceStatus.Error,
            "NODE_FAIL": ResourceStatus.Error,
            "OUT_OF_MEMORY": ResourceStatus.Error,
            "PENDING": ResourceStatus.Booting,
            "PREEMPTED": ResourceStatus.Deleted,
            "RUNNING": ResourceStatus.Running,
            "RESV_DEL_HOLD": ResourceStatus.Stopped,
            "REQUEUE_FED": ResourceStatus.Booting,
            "REQUEUE_HOLD": ResourceStatus.Booting,
            "REQUEUED": ResourceStatus.Booting,
            "RESIZING": ResourceStatus.Running,
            "REVOKED": ResourceStatus.Error,
            "SIGNALING": ResourceStatus.Running,
            "SPECIAL_EXIT": ResourceStatus.Booting,
            "STAGE_OUT": ResourceStatus.Running,
            "STOPPED": ResourceStatus.Stopped,
            "SUSPENDED": ResourceStatus.Stopped,
            "TIMEOUT": ResourceStatus.Error,
        }

        for id, value in enumerate(state_translations.values()):
            job_id = int(f"{id + 1000}000")
            returned_resource_attributes = run_async(
                self.slurm_adapter.resource_status,
                AttributeDict(remote_resource_uuid=job_id),
            )
            self.assertEqual(returned_resource_attributes.resource_status, value)

        self.mock_executor.return_value.run_command.called_once()

        self.mock_executor.return_value.run_command.assert_called_with(
            'squeue -o "%A|%N|%T" -h -t all'
        )

    def test_resource_status_raise_update_failed(self):
        # Update interval is 10 minutes, so turn back last update by 2 minutes
        # and creation date to current date, so that
        # TardisResourceStatusUpdateFailed is raised
        created_timestamp = datetime.now()
        new_timestamp = datetime.now() - timedelta(minutes=2)

        self.slurm_adapter._slurm_status._last_update = new_timestamp

        with self.assertRaises(TardisResourceStatusUpdateFailed):
            run_async(
                self.slurm_adapter.resource_status,
                AttributeDict(
                    remote_resource_uuid=1351043,
                    resource_state=ResourceStatus.Booting,
                    created=created_timestamp,
                ),
            )

    @mock_executor_run_command("")
    def test_resource_status_of_completed_jobs(self):
        # Update interval is 10 minutes, so turn back last update by 11 minutes
        # and creation date to 12 minutes ago. => squeue should be executed
        # The empty string returned by squeue represents a resource is already
        # gone. So, ResourceStatus returned should be Deleted.
        past_timestamp = datetime.now() - timedelta(minutes=12)
        new_timestamp = datetime.now() - timedelta(minutes=11)
        self.slurm_adapter._slurm_status._last_update = new_timestamp

        response = run_async(
            self.slurm_adapter.resource_status,
            AttributeDict(
                resource_id="1390065",
                remote_resource_uuid="1351043",
                created=past_timestamp,
            ),
        )

        self.assertEqual(response.resource_status, ResourceStatus.Deleted)

        self.mock_executor.return_value.run_command.assert_called_with(
            'squeue -o "%A|%N|%T" -h -t all'
        )

    @mock_executor_run_command(
        stdout="",
        raise_exception=CommandExecutionFailure(
            message="Failed", stdout="Failed", stderr="Failed", exit_code=2
        ),
    )
    def test_resource_status_update_failed(self):
        # set previous data, should be returned when update fails
        self.slurm_adapter._slurm_status._data = {
            "1390065": {"JobId": "1390065", "Host": "fh2n1552", "State": "RUNNING"}
        }

        with self.assertLogs(level=logging.WARNING):
            response = run_async(
                self.slurm_adapter.resource_status,
                AttributeDict(remote_resource_uuid="1390065"),
            )

        self.check_attribute_dicts(
            AttributeDict(
                remote_resource_uuid=1390065,
                resource_status=ResourceStatus.Running,
                updated=datetime.now(),
            ),
            response,
            exclude=("updated",),
        )

        self.mock_executor.return_value.run_command.assert_called_with(
            'squeue -o "%A|%N|%T" -h -t all'
        )

    @mock_executor_run_command(stdout="", stderr="", exit_code=0)
    def test_stop_resource(self):
        run_async(
            self.slurm_adapter.stop_resource,
            resource_attributes=self.resource_attributes,
        )

        self.mock_executor.return_value.run_command.assert_called_with(
            "scancel 1390065"
        )

    @mock_executor_run_command(stdout="", stderr="", exit_code=0)
    def test_terminate_resource(self):
        run_async(
            self.slurm_adapter.terminate_resource,
            resource_attributes=self.resource_attributes,
        )

        self.mock_executor.return_value.run_command.assert_called_with(
            "scancel 1390065"
        )

    def test_exception_handling(self):
        def test_exception_handling(to_raise, to_catch):
            with self.assertRaises(to_catch):
                with self.assertLogs(level=logging.WARNING):
                    with self.slurm_adapter.handle_exceptions():
                        raise to_raise

        matrix = [
            (asyncio.TimeoutError(), TardisTimeout),
            (
                CommandExecutionFailure(
                    message="Test", exit_code=255, stdout="Test", stderr="Test"
                ),
                TardisResourceStatusUpdateFailed,
            ),
            (TardisResourceStatusUpdateFailed, TardisResourceStatusUpdateFailed),
            (Exception, TardisError),
        ]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)
