from abc import ABCMeta
from abc import abstractmethod
from enum import Enum


class MachineStatus(Enum):
    Available = 1
    Draining = 2
    Drained = 3
    NotAvailable = 4


class BatchSystemAdapter(metaclass=ABCMeta):
    @abstractmethod
    async def disintegrate_machine(self, drone_uuid):
        return NotImplemented

    @abstractmethod
    async def drain_machine(self, drone_uuid):
        return NotImplemented

    @abstractmethod
    async def integrate_machine(self, drone_uuid):
        return NotImplemented

    @abstractmethod
    async def get_allocation(self, drone_uuid):
        return NotImplemented

    @abstractmethod
    async def get_machine_status(self, drone_uuid):
        return NotImplemented

    @abstractmethod
    async def get_utilization(self, drone_uuid):
        return NotImplemented
