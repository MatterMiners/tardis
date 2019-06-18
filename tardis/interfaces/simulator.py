from abc import ABCMeta, abstractmethod


class Simulator(metaclass=ABCMeta):
    @abstractmethod
    def get_value(self) -> float:
        return NotImplemented
