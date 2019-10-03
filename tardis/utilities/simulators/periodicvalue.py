from ...configuration.utilities import enable_yaml_load
from ...interfaces.simulator import Simulator

from datetime import datetime
from math import pi
from math import sin


@enable_yaml_load("!PeriodicValue")
class PeriodicValue(Simulator):
    def __init__(self, period, amplitude, offset=0, phase=0):
        self._period = period
        self._amplitude = amplitude
        self._phase = phase
        self._offset = offset
        self._start_time = datetime.now()

    def get_value(self) -> float:
        t = (datetime.now() - self._start_time).total_seconds()
        return self._offset + self._amplitude * sin(
            ((t / self._period) * 2 * pi) + self._phase)
