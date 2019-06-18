from ...configuration.utilities import enable_yaml_load
from ...interfaces.simulator import Simulator

import random


@enable_yaml_load("!RandomGauss")
class RandomGauss(Simulator):
    def __init__(self, mu, sigma, seed=None):
        self._mu = mu
        self._sigma = sigma
        random.seed(seed)

    def get_value(self) -> float:
        return random.gauss(self._mu, self._sigma)
