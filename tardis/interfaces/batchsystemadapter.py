from abc import ABCMeta
from abc import abstractmethod
from enum import Enum


class MachineActivities(Enum):
    Vacating = 1
    Killing = 2
    Idle = 3
    Busy = 4
    Suspended = 5
    Benchmarking = 6
    NotIntegrated = 7


class BatchSystemAdapter(metaclass=ABCMeta):
    @abstractmethod
    async def integrate_machine(self, dns_name):
        return NotImplemented

    @abstractmethod
    async def get_allocation(self, dns_name):
        return NotImplemented

    @abstractmethod
    async def get_machine_status(self, dns_name):
        return NotImplemented

    @abstractmethod
    async def get_utilization(self, dns_name):
        return NotImplemented
