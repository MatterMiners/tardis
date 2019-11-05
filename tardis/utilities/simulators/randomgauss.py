from ...configuration.utilities import enable_yaml_load
from ...interfaces.simulator import Simulator

import random


@enable_yaml_load("!RandomGauss")
class RandomGauss(Simulator):
    """
    Returns a random number drawn from a Gaussian distribution
    """

    def __init__(self, mu: float, sigma: float, seed: int = None):
        """
        :param mu: mean
        :type mu: float
        :param sigma: standard deviation
        :type sigma: float
        :param seed: random seed
        :type seed: int
        """
        self._mu = mu
        self._sigma = sigma
        random.seed(seed)

    def get_value(self) -> float:
        """
        Returns a random number drawn from a Gaussian distribution

        :return: random number drawn from a Gaussian distribution
        :rtype: float
        """
        return random.gauss(self._mu, self._sigma)
