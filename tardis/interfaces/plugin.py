from abc import ABCMeta
from abc import abstractmethod

from tardis.interfaces.state import State
from tardis.utilities.attributedict import AttributeDict


class Plugin(metaclass=ABCMeta):
    @abstractmethod
    async def notify(self, state: State, resource_attributes: AttributeDict) -> None:
        return NotImplemented
