from ..utilities.attributedict import AttributeDict

from abc import ABCMeta
from abc import abstractmethod
from enum import Enum


class MachineStatus(Enum):
    Available = 1
    Draining = 2
    Drained = 3
    NotAvailable = 4


class BatchSystemAdapter(metaclass=ABCMeta):
    """
    Abstract base class defining the interface for BatchSystemAdapters which handles
    integration and management of resources in the overlay batch system.
    """

    @abstractmethod
    async def disintegrate_machine(self, drone_uuid: str) -> None:
        """
        Disintegrate a machine from the overlay batch system.

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
                to the host name of the drone.
        :type drone_uuid: str
        :return: None
        """
        raise NotImplementedError

    @abstractmethod
    async def drain_machine(self, drone_uuid: str) -> None:
        """
        Drain a machine in the overlay batch system, which means that no new
        jobs will be accepted

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        :type drone_uuid: str
        :return: None
        """
        raise NotImplementedError

    @abstractmethod
    async def integrate_machine(self, drone_uuid: str) -> None:
        """
        Integrate a machine into the overlay batch system.

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        :type drone_uuid: str
        :return: None
        """
        raise NotImplementedError

    @abstractmethod
    async def get_allocation(self, drone_uuid: str) -> float:
        """
        Get the allocation of a worker node in the overlay batch system, which is
        defined as maximum of the ratios of requested over total resources
        (CPU, Memory, Disk, etc.).

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        :type drone_uuid: str
        :return: The allocation of a worker node as described above.
        :rtype: float
        """
        raise NotImplementedError

    @abstractmethod
    async def get_machine_status(self, drone_uuid: str) -> MachineStatus:
        """
        Get the status of a worker node in the overlay batch system (Available,
        Draining, Drained, NotAvailable)

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        :type drone_uuid: str
        :return: The machine status in HTCondor (Available, Draining, Drained,
            NotAvailable)
        :rtype: MachineStatus
        """
        raise NotImplementedError

    @abstractmethod
    async def get_utilisation(self, drone_uuid: str) -> float:
        """
        Get the utilisation of a worker node in the overlay batch system, which
        is defined as minimum of the ratios of requested over total resources
        (CPU, Memory, Disk, etc.).

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        :type drone_uuid: str
        :return: The utilisation of a worker node as described above.
        :rtype: float
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def machine_meta_data_translation_mapping(self) -> AttributeDict:
        """
        The machine meta data translation mapping is used to translate units of
        the machine meta data in ``TARDIS`` as expected by the overlay batch
        system.

        :return: machine meta data translation mapping
        :rtype: AttributeDict
        """
        raise NotImplementedError
