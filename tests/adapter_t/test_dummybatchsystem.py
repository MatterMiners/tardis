from tardis.adapter.batchsystems.dummybatchsystem import DummyBatchSystemAdapter
from tardis.interfaces.batchsystemadapter import MachineStatus

from ..utilities.utilities import run_async

from unittest.mock import patch
from unittest import TestCase


class TestDummyBatchSystemAdapter(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapter.batchsystems.dummybatchsystem.Configuration')
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        config.BatchSystem.allocation = 1.0
        config.BatchSystem.utilization = 1.0
        config.BatchSystem.machine_status = "Available"

        self.dummy_adapter = DummyBatchSystemAdapter()

    def test_disintegrate_machine(self):
        self.assertIsNone(run_async(self.dummy_adapter.disintegrate_machine, 'test-123'))

    def test_drain_machine(self):
        self.assertIsNone(run_async(self.dummy_adapter.drain_machine, 'test-123'))

    def test_integrate_machine(self):
        self.assertIsNone(run_async(self.dummy_adapter.integrate_machine, 'test-123'))

    def test_get_allocation(self):
        self.assertEqual(run_async(self.dummy_adapter.get_allocation, 'test-123'), 1.0)

    def test_get_machine_status(self):
        self.assertEqual(run_async(self.dummy_adapter.get_machine_status, 'test-123'), MachineStatus.Available)

    def test_get_utilization(self):
        self.assertEqual(run_async(self.dummy_adapter.get_utilization, 'test-123'), 1.0)
