from abc import ABCMeta
from abc import abstractmethod


class BatchSystemAdapter(metaclass=ABCMeta):
    @abstractmethod
    def integrate_machine(self, dns_name):
        return NotImplemented

    @abstractmethod
    def get_allocation(self, dns_name):
        return NotImplemented

    @abstractmethod
    def get_machine_status(self, dns_name):
        return NotImplemented

    @abstractmethod
    def get_utilization(self, dns_name):
        return NotImplemented
