from tests.utilities.utilities import async_return
from tests.utilities.utilities import run_async
from tardis.adapters.batchsystems.htcondor import HTCondorAdapter
from tardis.adapters.batchsystems.htcondor import htcondor_status_updater
from tardis.interfaces.batchsystemadapter import MachineStatus
from tardis.exceptions.executorexceptions import CommandExecutionFailure

from functools import partial
from shlex import quote
from unittest.mock import patch
from unittest import TestCase


class TestHTCondorAdapter(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapters.batchsystems.htcondor.Configuration')
        cls.mock_async_run_command_patcher = patch('tardis.adapters.batchsystems.htcondor.async_run_command')
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_async_run_command = cls.mock_async_run_command_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_async_run_command_patcher.stop()

    def setUp(self):
        self.cpu_ratio = 0.9
        self.memory_ratio = 0.8
        self.command = "condor_status -af:t Machine State Activity TardisDroneUuid " \
                       "'Real(TotalSlotCpus-Cpus)/TotalSlotCpus' " \
                       "'Real(TotalSlotMemory-Memory)/TotalSlotMemory' -constraint PartitionableSlot=?=True" \
                       " -pool my-htcondor.local -test"

        self.command_wo_options = "condor_status -af:t Machine State Activity TardisDroneUuid " \
                                  "'Real(TotalSlotCpus-Cpus)/TotalSlotCpus' " \
                                  "'Real(TotalSlotMemory-Memory)/TotalSlotMemory' -constraint PartitionableSlot=?=True"

        return_value = "\n".join([f"test\tUnclaimed\tIdle\tundefined\t{self.cpu_ratio}\t{self.memory_ratio}",
                                  f"test_drain\tDrained\tRetiring\tundefined\t{self.cpu_ratio}\t{self.memory_ratio}",
                                  f"test_drained\tDrained\tIdle\tundefined\t{self.cpu_ratio}\t{self.memory_ratio}",
                                  f"test_owner\tOwner\tIdle\tundefined\t{self.cpu_ratio}\t{self.memory_ratio}",
                                  f"test_uuid_plus\tUnclaimed\tIdle\ttest_uuid\t{self.cpu_ratio}\t{self.memory_ratio}",
                                  "exoscale-26d361290f\tUnclaimed\tIdle\tundefined\t0.125\t0.125"])
        self.mock_async_run_command.return_value = async_return(return_value=return_value)

        self.setup_config_mock(options={'pool': 'my-htcondor.local',
                                        'test': None})

        self.htcondor_adapter = HTCondorAdapter()

    def tearDown(self):
        self.mock_async_run_command.reset_mock()

    def setup_config_mock(self, options=None):
        self.config = self.mock_config.return_value
        self.config.BatchSystem.ratios = {'cpu_ratio': 'Real(TotalSlotCpus-Cpus)/TotalSlotCpus',
                                          'memory_ratio': 'Real(TotalSlotMemory-Memory)/TotalSlotMemory'}
        self.config.BatchSystem.max_age = 10
        if options:
            self.config.BatchSystem.options = options
        else:
            self.config.BatchSystem.options = {}

    def test_disintegrate_machine(self):
        self.assertIsNone(run_async(self.htcondor_adapter.disintegrate_machine, drone_uuid='test'))

    def test_drain_machine(self):
        run_async(self.htcondor_adapter.drain_machine, drone_uuid='test')
        self.mock_async_run_command.assert_called_with('condor_drain -pool my-htcondor.local -test -graceful test')
        self.assertIsNone(run_async(self.htcondor_adapter.drain_machine, drone_uuid="not_exists"))
        self.mock_async_run_command.side_effect = CommandExecutionFailure(message="Does not exists",
                                                                          exit_code=1,
                                                                          stderr="Does not exists")
        self.assertIsNone(run_async(self.htcondor_adapter.drain_machine, drone_uuid="test"))

        self.mock_async_run_command.side_effect = CommandExecutionFailure(message="Unhandled error",
                                                                          exit_code=2,
                                                                          stderr="Unhandled error")
        with self.assertRaises(CommandExecutionFailure):
            self.assertIsNone(run_async(self.htcondor_adapter.drain_machine, drone_uuid="test"))

        self.mock_async_run_command.side_effect = None

    def test_drain_machine_without_options(self):
        self.setup_config_mock()
        self.htcondor_adapter = HTCondorAdapter()

        run_async(self.htcondor_adapter.drain_machine, drone_uuid='test')
        self.mock_async_run_command.assert_called_with('condor_drain -graceful test')

    def test_integrate_machine(self):
        self.assertIsNone(run_async(self.htcondor_adapter.integrate_machine, drone_uuid='test'))

    def test_get_resource_ratios(self):
        self.assertCountEqual(list(run_async(self.htcondor_adapter.get_resource_ratios, drone_uuid='test')),
                              [self.cpu_ratio, self.memory_ratio])
        self.mock_async_run_command.assert_called_with(self.command)

        self.assertEqual(run_async(self.htcondor_adapter.get_resource_ratios, drone_uuid='not_exists'), {})

    def test_get_resource_ratios_without_options(self):
        self.setup_config_mock()
        del self.config.BatchSystem.options
        self.htcondor_adapter = HTCondorAdapter()

        self.assertCountEqual(list(run_async(self.htcondor_adapter.get_resource_ratios, drone_uuid='test')),
                             [self.cpu_ratio, self.memory_ratio])

        self.mock_async_run_command.assert_called_with(self.command_wo_options)

    def test_get_allocation(self):
        self.assertEqual(run_async(self.htcondor_adapter.get_allocation, drone_uuid='test'),
                         max([self.cpu_ratio, self.memory_ratio]))
        self.mock_async_run_command.assert_called_with(self.command)

    def test_get_machine_status(self):
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, drone_uuid='test'),
                         MachineStatus.Available)
        self.mock_async_run_command.assert_called_with(self.command)
        self.mock_async_run_command.reset_mock()
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, drone_uuid='not_exists'),
                         MachineStatus.NotAvailable)
        self.mock_async_run_command.reset_mock()
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, drone_uuid='test_drain'),
                         MachineStatus.Draining)
        self.mock_async_run_command.reset_mock()
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, drone_uuid='test_drained'),
                         MachineStatus.Drained)
        self.mock_async_run_command.reset_mock()
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, drone_uuid='test_owner'),
                         MachineStatus.NotAvailable)
        self.mock_async_run_command.reset_mock()

        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, drone_uuid='test_uuid'),
                         MachineStatus.Available)
        self.mock_async_run_command.reset_mock()

        self.mock_async_run_command.side_effect = CommandExecutionFailure(message="Test", exit_code=123,
                                                                          stderr="Test")
        with self.assertLogs(level='ERROR'):
            with self.assertRaises(CommandExecutionFailure):
                attributes = {"Machine": "Machine", "State": "State",
                              "Activity": "Activity",
                              "TardisDroneUuid": "TardisDroneUuid"}
                # Escape htcondor expressions and add them to attributes
                attributes.update({key: quote(value) for key, value in
                                   self.config.BatchSystem.ratios.items()})
                run_async(
                    partial(htcondor_status_updater, self.config.BatchSystem.options,
                            attributes))
                self.mock_async_run_command.assert_called_with(self.command)
        self.mock_async_run_command.side_effect = None

    def test_get_utilization(self):
        self.assertEqual(run_async(self.htcondor_adapter.get_utilization, drone_uuid='test'),
                         min([self.cpu_ratio, self.memory_ratio]))
        self.mock_async_run_command.assert_called_with(self.command)
