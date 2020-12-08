from ...configuration.configuration import Configuration
from ...interfaces.batchsystemadapter import BatchSystemAdapter
from ...interfaces.batchsystemadapter import MachineStatus
from ...utilities.attributedict import AttributeDict


class FakeBatchSystemAdapter(BatchSystemAdapter):
    """
    :py:class:`~tardis.adapters.batchsystems.fakebatchsystem.FakeBatchSystemAdapter`
    implements a batch system adapter that mocks the response of a hypothetical
    batch system. It can be used for testing purposes and as a demonstrator
    in workshops and tutorials.

    The mocked response to the :py:meth:`~.get_utilisation`, :py:meth:`~.get_allocation`
    and :py:meth:`~.get_machine_status` API calls is configurable statically.
    """

    def __init__(self):
        config = Configuration()
        self.fake_config = config.BatchSystem
        self._drained_machines = {}

    async def disintegrate_machine(self, drone_uuid: str) -> None:
        """
        FakeBatchSystemAdapter's do nothing disintegrate_machine implementation

        :param drone_uuid: Unique identifier of the drone
        :type drone_uuid: str
        """
        return

    async def drain_machine(self, drone_uuid: str) -> None:
        """
        FakeBatchSystemAdapter's do nothing drain_machine implementation

        :param drone_uuid: Unique identifier of the drone
        :type drone_uuid: str
        """
        self._drained_machines[drone_uuid] = MachineStatus.Drained
        return

    async def integrate_machine(self, drone_uuid: str) -> None:
        """
        FakeBatchSystemAdapter's do nothing integrate_machine implementation

        :param drone_uuid: Unique identifier of the drone
        :type drone_uuid: str
        """
        return

    async def get_allocation(self, drone_uuid: str) -> float:
        """
        Returns the fake allocation according to the configuration of the
        FakeBatchSystem

        :param drone_uuid: Unique identifier of the drone
        :type drone_uuid: str
        :return: Allocation value specified in the FakeBatchSystem configuration
        :rtype: float
        """
        try:
            allocation = self.fake_config.allocation.get_value()
        except AttributeError:
            return self.fake_config.allocation
        else:
            return allocation

    async def get_machine_status(self, drone_uuid: str) -> MachineStatus:
        """
        Returns a fake machine status according to the parameter set in the
        configuration of the FakeBatchSystem

        :param drone_uuid: Unique identifier of the drone
        :type drone_uuid: str
        :return: Machine status specified in the FakeBatchSystem configuration
        :rtype: MachineStatus
        """
        try:
            machine_status = self._drained_machines[drone_uuid]
        except KeyError:
            return getattr(MachineStatus, self.fake_config.machine_status)
        else:
            return machine_status

    async def get_utilisation(self, drone_uuid: str) -> float:
        """
        Returns the fake utilisation according to the configuration of the
        FakeBatchSystem

        :param drone_uuid: Unique identifier of the drone
        :type drone_uuid: str
        :return: utilisation value specified in the FakeBatchSystem configuration
        :rtype: float
        """
        try:
            utilisation = self.fake_config.utilisation.get_value()
        except AttributeError:
            return self.fake_config.utilisation
        else:
            return utilisation

    @property
    def machine_meta_data_translation_mapping(self) -> AttributeDict:
        """
        The machine meta data translation mapping is used to translate units of
        the machine meta data in ``TARDIS`` to values expected by the
        FakeBatchSystem adapter.

        :return: Machine meta data translation mapping
        :rtype: AttributeDict
        """
        return AttributeDict(Cores=1, Memory=1, Disk=1)
