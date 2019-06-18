from tardis.adapters.batchsystems.fakebatchsystem import FakeBatchSystemAdapter
from tardis.interfaces.batchsystemadapter import MachineStatus

from tests.utilities.utilities import run_async

from unittest.mock import patch
from unittest import TestCase


class TestFakeBatchSystemAdapter(TestCase):
    mock_config_patcher = None
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapters.batchsystems.fakebatchsystem.Configuration')
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        config.BatchSystem.allocation = 1.0
        config.BatchSystem.utilization = 1.0
        config.BatchSystem.machine_status = "Available"

        self.fake_adapter = FakeBatchSystemAdapter()

    def test_disintegrate_machine(self):
        self.assertIsNone(run_async(self.fake_adapter.disintegrate_machine, 'test-123'))

    def test_drain_machine(self):
        self.assertIsNone(run_async(self.fake_adapter.drain_machine, 'test-123'))

    def test_integrate_machine(self):
        self.assertIsNone(run_async(self.fake_adapter.integrate_machine, 'test-123'))

    def test_get_allocation(self):
        self.assertEqual(run_async(self.fake_adapter.get_allocation, 'test-123'), 1.0)

    def test_get_machine_status(self):
        self.assertEqual(run_async(self.fake_adapter.get_machine_status, 'test-123'), MachineStatus.Available)

        run_async(self.fake_adapter.drain_machine, 'test-123')
        self.assertEqual(run_async(self.fake_adapter.get_machine_status, 'test-123'), MachineStatus.Drained)

    def test_get_utilization(self):
        self.assertEqual(run_async(self.fake_adapter.get_utilization, 'test-123'), 1.0)
