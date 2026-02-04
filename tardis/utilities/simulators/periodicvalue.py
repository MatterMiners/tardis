from ...configuration.utilities import enable_yaml_load
from ...interfaces.simulator import Simulator

from datetime import datetime
from math import pi
from math import sin


@enable_yaml_load("!PeriodicValue")
class PeriodicValue(Simulator):
    """
    Provides a time-periodic sinusoidally varying value relative to the time the object
    was created.
    """

    def __init__(
        self, period: float, amplitude: float, offset: float = 0, phase: float = 0
    ):
        """
        :param period: period of the sine wave in seconds
        :param amplitude: amplitude of the sine wave
        :param offset: offset of the sine wave
        :param phase: phase of the sine wave in seconds
        """
        self._period = period
        self._amplitude = amplitude
        self._phase = phase
        self._offset = offset
        self._start_time = datetime.now()

    def get_value(self) -> float:
        """
        Returns the current value relative to the time of initialization.

        :return: current value of sine wave
        """
        t = (datetime.now() - self._start_time).total_seconds()
        return self._offset + self._amplitude * sin(
            ((t / self._period) * 2 * pi) + self._phase
        )
