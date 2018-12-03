from ..utilities.utilities import run_async
from ..utilities.utilities import async_return
from tardis.agents.batchsystemagent import BatchSystemAgent
from tardis.interfaces.batchsystemadapter import BatchSystemAdapter

from unittest import TestCase
from unittest.mock import create_autospec


class TestBatchSystemAgent(TestCase):
    def setUp(self):
        self.batch_system_adapter = create_autospec(BatchSystemAdapter)
        self.batch_system_agent = BatchSystemAgent(self.batch_system_adapter)

    def test_disintegrate_machine(self):
        self.batch_system_adapter.disintegrate_machine.side_effect = async_return
        run_async(self.batch_system_agent.disintegrate_machine, dns_name='test')
        self.batch_system_adapter.disintegrate_machine.assert_called_with('test')

    def test_drain_machine(self):
        self.batch_system_adapter.drain_machine.side_effect = async_return
        run_async(self.batch_system_agent.drain_machine, dns_name='test')
        self.batch_system_adapter.drain_machine.assert_called_with('test')

    def test_integrate_machine(self):
        self.batch_system_adapter.integrate_machine.side_effect = async_return
        run_async(self.batch_system_agent.integrate_machine, dns_name='test')
        self.batch_system_adapter.integrate_machine.assert_called_with('test')

    def test_get_allocation(self):
        self.batch_system_adapter.get_allocation.side_effect = async_return
        run_async(self.batch_system_agent.get_allocation, dns_name='test')
        self.batch_system_adapter.get_allocation.assert_called_with('test')

    def test_get_machine_status(self):
        self.batch_system_adapter.get_machine_status.side_effect = async_return
        run_async(self.batch_system_agent.get_machine_status, dns_name='test')
        self.batch_system_adapter.get_machine_status.assert_called_with('test')

    def test_get_utilization(self):
        self.batch_system_adapter.get_utilization.side_effect = async_return
        run_async(self.batch_system_agent.get_utilization, dns_name='test')
        self.batch_system_adapter.get_utilization.assert_called_with('test')
