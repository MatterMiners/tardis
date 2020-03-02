from tardis.adapters.batchsystems.fakebatchsystem import FakeBatchSystemAdapter
from tardis.interfaces.batchsystemadapter import MachineStatus
from tardis.utilities.attributedict import AttributeDict

from tests.utilities.utilities import run_async

from unittest.mock import patch
from unittest import TestCase


class TestFakeBatchSystemAdapter(TestCase):
    mock_config_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch(
            "tardis.adapters.batchsystems.fakebatchsystem.Configuration"
        )
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()

    def setUp(self):
        self.config = self.mock_config.return_value
        self.config.BatchSystem.allocation = 1.0
        self.config.BatchSystem.utilisation = 1.0
        self.config.BatchSystem.machine_status = "Available"

        self.fake_adapter = FakeBatchSystemAdapter()

    def test_disintegrate_machine(self):
        self.assertIsNone(run_async(self.fake_adapter.disintegrate_machine, "test-123"))

    def test_drain_machine(self):
        self.assertIsNone(run_async(self.fake_adapter.drain_machine, "test-123"))

    def test_integrate_machine(self):
        self.assertIsNone(run_async(self.fake_adapter.integrate_machine, "test-123"))

    def test_get_allocation(self):
        self.assertEqual(run_async(self.fake_adapter.get_allocation, "test-123"), 1.0)

        self.config.BatchSystem.allocation = AttributeDict(get_value=lambda: 0.9)
        self.fake_adapter = FakeBatchSystemAdapter()
        self.assertEqual(run_async(self.fake_adapter.get_allocation, "test-123"), 0.9)

    def test_get_machine_status(self):
        self.assertEqual(
            run_async(self.fake_adapter.get_machine_status, "test-123"),
            MachineStatus.Available,
        )

        run_async(self.fake_adapter.drain_machine, "test-123")
        self.assertEqual(
            run_async(self.fake_adapter.get_machine_status, "test-123"),
            MachineStatus.Drained,
        )

    def test_get_utilisation(self):
        self.assertEqual(run_async(self.fake_adapter.get_utilisation, "test-123"), 1.0)

        self.config.BatchSystem.utilisation = AttributeDict(get_value=lambda: 0.9)
        self.fake_adapter = FakeBatchSystemAdapter()
        self.assertEqual(run_async(self.fake_adapter.get_utilisation, "test-123"), 0.9)
