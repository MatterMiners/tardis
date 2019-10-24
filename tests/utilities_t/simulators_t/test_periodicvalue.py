from tardis.utilities.simulators.periodicvalue import PeriodicValue

from unittest import TestCase
import yaml


class TestPeriodicValue(TestCase):
    def setUp(self) -> None:
        self.simulator = PeriodicValue(period=3600, amplitude=0.5, offset=0.5, phase=0)

    def test_get_value(self):
        self.assertIsInstance(self.simulator.get_value(), float)
        self.assertLessEqual(self.simulator.get_value(), 1.0)

    def test_construction_by_yaml(self):
        periodic_value = yaml.safe_load(
            """!PeriodicValue
                                           period: 3600
                                           amplitude: 0.5
                                           offset: 0.5
                                           phase: 0"""
        )
        self.assertIsInstance(periodic_value.get_value(), float)
