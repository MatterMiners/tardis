from tardis.utilities.simulators.randomgauss import RandomGauss

from unittest import TestCase

import yaml


class TestRandomGauss(TestCase):
    def setUp(self) -> None:
        self.random_gauss = RandomGauss(0, 1)

    def test_get_value(self):
        value = self.random_gauss.get_value()
        self.assertIsInstance(value, float)
        self.assertLess(value, 10)
        self.assertGreater(value, -10)

    def test_construction_by_yaml(self):
        random_gauss = yaml.safe_load(
            """
                              !RandomGauss
                              mu: 0
                              sigma: 1
                              """
        )
        self.assertIsInstance(random_gauss.get_value(), float)
