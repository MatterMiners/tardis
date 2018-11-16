from abc import ABCMeta
from abc import abstractmethod


class Observer(metaclass=ABCMeta):
    @abstractmethod
    def notify(self, state, resource_attributes):
        return NotImplemented
