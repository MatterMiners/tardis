from tardis.adapters.sites.htcondor import HTCondorAdapter
from tardis.exceptions.executorexceptions import CommandExecutionFailure
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.utilities.attributedict import AttributeDict
from ...utilities.utilities import mock_executor_run_command
from ...utilities.utilities import run_async

from datetime import datetime
from datetime import timedelta
from unittest import TestCase
from unittest.mock import patch

import logging

CONDOR_SUBMIT_OUTPUT = """Submitting job(s).
1 job(s) submitted to cluster 1351043."""

CONDOR_Q_OUTPUT_IDLE = "test\t1\t1351043\t0"
CONDOR_Q_OUTPUT_RUN = "test\t2\t1351043\t0"
CONDOR_Q_OUTPUT_REMOVING = "test\t3\t1351043\t0"
CONDOR_Q_OUTPUT_COMPLETED = "test\t4\t1351043\t0"
CONDOR_Q_OUTPUT_HELD = "test\t5\t1351043\t0"
CONDOR_Q_OUTPUT_TRANSFERING_OUTPUT = "test\t6\t1351043\t0"
CONDOR_Q_OUTPUT_SUSPENDED = "test\t7\t1351043\t0"

CONDOR_RM_OUTPUT = """All jobs in cluster 1351043 have been marked for removal"""
CONDOR_RM_FAILED_OUTPUT = """Couldn't find/remove all jobs in cluster 1351043"""
CONDOR_RM_FAILED_MESSAGE = """Run command condor_rm 1351043 via ShellExecutor failed"""

CONDOR_SUSPEND_OUTPUT = """All jobs in cluster 1351043 have been suspended"""
CONDOR_SUSPEND_FAILED_OUTPUT = """Couldn't find/suspend all jobs in cluster 1351043"""
CONDOR_SUSPEND_FAILED_MESSAGE = """Run command condor_suspend 1351043 via
ShellExecutor failed"""

CONDOR_SUBMIT_JDL_CONDOR_OBS = """executable = start_pilot.sh
transfer_input_files = setup_pilot.sh
output = logs/$(cluster).$(process).out
error = logs/$(cluster).$(process).err
log = logs/cluster.log

accounting_group=tardis

environment=TardisDroneCores=8;TardisDroneMemory=32768;TardisDroneDisk=167772160;TardisDroneUuid=test-123

request_cpus=8
request_memory=32768
request_disk=167772160

queue 1"""  # noqa: B950

CONDOR_SUBMIT_JDL_SPARK_OBS = """executable = start_pilot.sh
transfer_input_files = setup_pilot.sh
output = logs/$(cluster).$(process).out
error = logs/$(cluster).$(process).err
log = logs/cluster.log

accounting_group=tardis

environment=TardisDroneCores=8;TardisDroneMemory=32;TardisDroneDisk=160;TardisDroneUuid=test-123

request_cpus=8
request_memory=32768
request_disk=167772160

queue 1"""  # noqa: B950


class TestHTCondorSiteAdapter(TestCase):
    mock_config_patcher = None
    mock_executor_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch("tardis.interfaces.siteadapter.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_executor_patcher = patch(
            "tardis.adapters.sites.htcondor.ShellExecutor"
        )
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
        test_site_config.max_age = 10

        self.adapter = HTCondorAdapter(machine_type="test2large", site_name="TestSite")

    @property
    def machine_meta_data(self):
        return AttributeDict(
            test2large=AttributeDict(Cores=8, Memory=32, Disk=160),
            testunkownresource=AttributeDict(Cores=8, Memory=32, Disk=160, Foo=3),
        )

    @property
    def machine_type_configuration(self):
        return AttributeDict(
            test2large=AttributeDict(jdl="tests/data/submit.jdl"),
            testunkownresource=AttributeDict(jdl="tests/data/submit.jdl"),
        )

    @mock_executor_run_command(stdout=CONDOR_SUBMIT_OUTPUT)
    def test_deploy_resource_htcondor_obs(self):
        response = run_async(
            self.adapter.deploy_resource,
            AttributeDict(
                drone_uuid="test-123",
                obs_machine_meta_data_translation_mapping=AttributeDict(
                    Cores=1,
                    Memory=1024,
                    Disk=1024 * 1024,
                ),
            ),
        )
        self.assertEqual(response.remote_resource_uuid, "1351043")
        self.assertFalse(response.created - datetime.now() > timedelta(seconds=1))
        self.assertFalse(response.updated - datetime.now() > timedelta(seconds=1))

        self.mock_executor.return_value.run_command.assert_called_with(
            "condor_submit", stdin_input=CONDOR_SUBMIT_JDL_CONDOR_OBS
        )
        self.mock_executor.reset()

        run_async(
            self.adapter.deploy_resource,
            AttributeDict(
                drone_uuid="test-123",
                obs_machine_meta_data_translation_mapping=AttributeDict(
                    Cores=1,
                    Memory=1,
                    Disk=1,
                ),
            ),
        )

        self.mock_executor.return_value.run_command.assert_called_with(
            "condor_submit", stdin_input=CONDOR_SUBMIT_JDL_SPARK_OBS
        )
        self.mock_executor.reset()

    def test_translate_resources_raises_logs(self):
        self.adapter = HTCondorAdapter(
            machine_type="testunkownresource", site_name="TestSite"
        )
        with self.assertLogs(logging.getLogger(), logging.ERROR):
            with self.assertRaises(KeyError):
                run_async(
                    self.adapter.deploy_resource,
                    AttributeDict(
                        drone_uuid="test-123",
                        obs_machine_meta_data_translation_mapping=AttributeDict(
                            Cores=1,
                            Memory=1024,
                            Disk=1024 * 1024,
                        ),
                    ),
                )

    def test_machine_meta_data(self):
        self.assertEqual(
            self.adapter.machine_meta_data, self.machine_meta_data.test2large
        )

    def test_machine_type(self):
        self.assertEqual(self.adapter.machine_type, "test2large")

    def test_site_name(self):
        self.assertEqual(self.adapter.site_name, "TestSite")

    @mock_executor_run_command(stdout=CONDOR_Q_OUTPUT_IDLE)
    def test_resource_status_idle(self):
        response = run_async(
            self.adapter.resource_status, AttributeDict(remote_resource_uuid="1351043")
        )
        self.assertEqual(response.resource_status, ResourceStatus.Booting)

    @mock_executor_run_command(stdout=CONDOR_Q_OUTPUT_RUN)
    def test_resource_status_run(self):
        response = run_async(
            self.adapter.resource_status, AttributeDict(remote_resource_uuid="1351043")
        )
        self.assertEqual(response.resource_status, ResourceStatus.Running)

    @mock_executor_run_command(stdout=CONDOR_Q_OUTPUT_REMOVING)
    def test_resource_status_removing(self):
        response = run_async(
            self.adapter.resource_status, AttributeDict(remote_resource_uuid="1351043")
        )
        self.assertEqual(response.resource_status, ResourceStatus.Running)

    @mock_executor_run_command(stdout=CONDOR_Q_OUTPUT_COMPLETED)
    def test_resource_status_completed(self):
        response = run_async(
            self.adapter.resource_status, AttributeDict(remote_resource_uuid="1351043")
        )
        self.assertEqual(response.resource_status, ResourceStatus.Deleted)

    @mock_executor_run_command(stdout=CONDOR_Q_OUTPUT_HELD)
    def test_resource_status_held(self):
        response = run_async(
            self.adapter.resource_status, AttributeDict(remote_resource_uuid="1351043")
        )
        self.assertEqual(response.resource_status, ResourceStatus.Error)

    @mock_executor_run_command(stdout=CONDOR_Q_OUTPUT_TRANSFERING_OUTPUT)
    def test_resource_status_transfering_output(self):
        response = run_async(
            self.adapter.resource_status, AttributeDict(remote_resource_uuid="1351043")
        )
        self.assertEqual(response.resource_status, ResourceStatus.Running)

    @mock_executor_run_command(stdout=CONDOR_Q_OUTPUT_SUSPENDED)
    def test_resource_status_unexpanded(self):
        response = run_async(
            self.adapter.resource_status, AttributeDict(remote_resource_uuid="1351043")
        )
        self.assertEqual(response.resource_status, ResourceStatus.Stopped)

    @mock_executor_run_command(
        stdout="",
        raise_exception=CommandExecutionFailure(
            message="Failed", stdout="Failed", stderr="Failed", exit_code=2
        ),
    )
    def test_resource_status_raise_future(self):
        future_timestamp = datetime.now() + timedelta(minutes=1)
        with self.assertLogs(level=logging.WARNING):
            with self.assertRaises(TardisResourceStatusUpdateFailed):
                run_async(
                    self.adapter.resource_status,
                    AttributeDict(
                        remote_resource_uuid="1351043", created=future_timestamp
                    ),
                )

    @mock_executor_run_command(
        stdout="",
        raise_exception=CommandExecutionFailure(
            message="Failed", stdout="Failed", stderr="Failed", exit_code=2
        ),
    )
    def test_resource_status_raise_past(self):
        # Update interval is 10 minutes, so set last update back by 11 minutes
        # in order to execute condor_q command and creation date to 12 minutes ago
        past_timestamp = datetime.now() - timedelta(minutes=12)
        self.adapter._htcondor_queue._last_update = datetime.now() - timedelta(
            minutes=11
        )
        with self.assertLogs(level=logging.WARNING):
            response = run_async(
                self.adapter.resource_status,
                AttributeDict(remote_resource_uuid="1351043", created=past_timestamp),
            )
        self.assertEqual(response.resource_status, ResourceStatus.Deleted)

    @mock_executor_run_command(stdout=CONDOR_SUSPEND_OUTPUT)
    def test_stop_resource(self):
        response = run_async(
            self.adapter.stop_resource, AttributeDict(remote_resource_uuid="1351043")
        )
        self.assertEqual(response.remote_resource_uuid, "1351043")

    @mock_executor_run_command(
        stdout="",
        raise_exception=CommandExecutionFailure(
            message=CONDOR_SUSPEND_FAILED_MESSAGE,
            exit_code=1,
            stderr=CONDOR_SUSPEND_FAILED_OUTPUT,
            stdout="",
            stdin="",
        ),
    )
    def test_stop_resource_failed_redo(self):
        with self.assertRaises(TardisResourceStatusUpdateFailed):
            run_async(
                self.adapter.stop_resource,
                AttributeDict(remote_resource_uuid="1351043"),
            )

    @mock_executor_run_command(
        stdout="",
        raise_exception=CommandExecutionFailure(
            message=CONDOR_SUSPEND_FAILED_MESSAGE,
            exit_code=2,
            stderr=CONDOR_SUSPEND_FAILED_OUTPUT,
            stdout="",
            stdin="",
        ),
    )
    def test_stop_resource_failed_raise(self):
        with self.assertRaises(CommandExecutionFailure):
            run_async(
                self.adapter.stop_resource,
                AttributeDict(remote_resource_uuid="1351043"),
            )

    @mock_executor_run_command(stdout=CONDOR_RM_OUTPUT)
    def test_terminate_resource(self):
        response = run_async(
            self.adapter.terminate_resource,
            AttributeDict(remote_resource_uuid="1351043"),
        )
        self.assertEqual(response.remote_resource_uuid, "1351043")

    @mock_executor_run_command(
        stdout="",
        raise_exception=CommandExecutionFailure(
            message=CONDOR_RM_FAILED_MESSAGE,
            exit_code=1,
            stderr=CONDOR_RM_FAILED_OUTPUT,
            stdout="",
            stdin="",
        ),
    )
    def test_terminate_resource_failed_redo(self):
        with self.assertRaises(TardisResourceStatusUpdateFailed):
            run_async(
                self.adapter.terminate_resource,
                AttributeDict(remote_resource_uuid="1351043"),
            )

    @mock_executor_run_command(
        stdout="",
        raise_exception=CommandExecutionFailure(
            message=CONDOR_RM_FAILED_MESSAGE,
            exit_code=2,
            stderr=CONDOR_RM_FAILED_OUTPUT,
            stdout="",
            stdin="",
        ),
    )
    def test_terminate_resource_failed_raise(self):
        with self.assertRaises(CommandExecutionFailure):
            run_async(
                self.adapter.terminate_resource,
                AttributeDict(remote_resource_uuid="1351043"),
            )

    def test_exception_handling(self):
        def test_exception_handling(raise_it, catch_it):
            with self.assertRaises(catch_it):
                with self.adapter.handle_exceptions():
                    raise raise_it

        matrix = [
            (Exception, TardisError),
            (TardisResourceStatusUpdateFailed, TardisResourceStatusUpdateFailed),
        ]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)
