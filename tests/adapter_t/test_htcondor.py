from ..utilities.utilities import async_return
from ..utilities.utilities import run_async
from tardis.adapter.batchsystems.htcondor import HTCondorAdapter
from tardis.adapter.batchsystems.htcondor import htcondor_status_updater
from tardis.interfaces.batchsystemadapter import MachineStatus
from tardis.exceptions.tardisexceptions import AsyncRunCommandFailure

from unittest.mock import patch
from unittest import TestCase


class TestHTCondorAdapter(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapter.batchsystems.htcondor.Configuration')
        cls.mock_async_run_command_patcher = patch('tardis.adapter.batchsystems.htcondor.async_run_command')
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_async_run_command = cls.mock_async_run_command_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_async_run_command_patcher.stop()

    def setUp(self):
        self.cpu_ratio = 0.9
        self.memory_ratio = 0.8
        self.command = "condor_status -af:t Machine State Activity 'Real(TotalSlotCpus-Cpus)/TotalSlotCpus' " \
                       "'Real(TotalSlotCpus-Cpus)/TotalSlotCpus' -constraint PartitionableSlot=?=True"

        return_value = "\n".join([f"test\tUnclaimed\tIdle\t{self.cpu_ratio}\t{self.memory_ratio}",
                                  f"test_drain\tDrained\tRetiring\t{self.cpu_ratio}\t{self.memory_ratio}",
                                  f"test_drained\tDrained\tIdle\t{self.cpu_ratio}\t{self.memory_ratio}",
                                  f"test_owner\tOwner\tIdle\t{self.cpu_ratio}\t{self.memory_ratio}",
                                  "exoscale-26d361290f\tUnclaimed\tIdle\t0.125\t0.125"])
        self.mock_async_run_command.return_value = async_return(return_value=return_value)

        config = self.mock_config.return_value
        config.BatchSystem.ratios = {'cpu_ratio': 'Real(TotalSlotCpus-Cpus)/TotalSlotCpus',
                                     'memory_ratio': 'Real(TotalSlotCpus-Cpus)/TotalSlotCpus'}
        config.BatchSystem.max_age = 10

        self.htcondor_adapter = HTCondorAdapter()

    def tearDown(self):
        self.mock_async_run_command.reset_mock()

    def test_disintegrate_machine(self):
        self.assertIsNone(run_async(self.htcondor_adapter.disintegrate_machine, dns_name='test'))

    def test_drain_machine(self):
        run_async(self.htcondor_adapter.drain_machine, dns_name='test')
        self.mock_async_run_command.assert_called_with('condor_drain -graceful test')
        self.assertIsNone(run_async(self.htcondor_adapter.drain_machine, dns_name="not_exists"))
        self.mock_async_run_command.side_effect = AsyncRunCommandFailure(message="Does not exists",
                                                                         error_code=1,
                                                                         error_message="Does not exists")
        self.assertIsNone(run_async(self.htcondor_adapter.drain_machine, dns_name="test"))

        self.mock_async_run_command.side_effect = AsyncRunCommandFailure(message="Unhandled error",
                                                                         error_code=2,
                                                                         error_message="Unhandled error")
        with self.assertRaises(AsyncRunCommandFailure):
            self.assertIsNone(run_async(self.htcondor_adapter.drain_machine, dns_name="test"))

        self.mock_async_run_command.side_effect = None

    def test_integrate_machine(self):
        self.assertIsNone(run_async(self.htcondor_adapter.integrate_machine, dns_name='test'))

    def test_get_resource_ratios(self):
        self.assertCountEqual(list(run_async(self.htcondor_adapter.get_resource_ratios, dns_name='test')),
                              [self.cpu_ratio, self.memory_ratio])
        self.mock_async_run_command.assert_called_with(self.command)

        self.assertEqual(run_async(self.htcondor_adapter.get_resource_ratios, dns_name='not_exists'), {})

    def test_get_allocation(self):
        self.assertEqual(run_async(self.htcondor_adapter.get_allocation, dns_name='test'),
                         max([self.cpu_ratio, self.memory_ratio]))
        self.mock_async_run_command.assert_called_with(self.command)

    def test_get_machine_status(self):
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, dns_name='test'),
                         MachineStatus.Available)
        self.mock_async_run_command.assert_called_with(self.command)
        self.mock_async_run_command.reset_mock()
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, dns_name='not_exists'),
                         MachineStatus.NotAvailable)
        self.mock_async_run_command.reset_mock()
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, dns_name='test_drain'),
                         MachineStatus.Draining)
        self.mock_async_run_command.reset_mock()
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, dns_name='test_drained'),
                         MachineStatus.Drained)
        self.mock_async_run_command.reset_mock()
        self.assertEqual(run_async(self.htcondor_adapter.get_machine_status, dns_name='test_owner'),
                         MachineStatus.NotAvailable)
        self.mock_async_run_command.reset_mock()

        self.mock_async_run_command.side_effect = AsyncRunCommandFailure(message="Test", error_code=123,
                                                                         error_message="Test")
        with self.assertLogs(level='ERROR'):
            run_async(htcondor_status_updater)
            self.mock_async_run_command.assert_called_with(self.command)
        self.mock_async_run_command.side_effect = None

    def test_get_utilization(self):
        self.assertEqual(run_async(self.htcondor_adapter.get_utilization, dns_name='test'),
                         min([self.cpu_ratio, self.memory_ratio]))
        self.mock_async_run_command.assert_called_with(self.command)
