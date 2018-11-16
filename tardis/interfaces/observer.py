from abc import ABCMeta
from abc import abstractmethod


class Observer(metaclass=ABCMeta):
    @abstractmethod
    async def notify(self, state, resource_attributes):
        return NotImplemented
