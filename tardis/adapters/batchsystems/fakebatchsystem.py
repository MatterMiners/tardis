from tardis.configuration.configuration import Configuration
from tardis.interfaces.batchsystemadapter import BatchSystemAdapter
from tardis.interfaces.batchsystemadapter import MachineStatus


class FakeBatchSystemAdapter(BatchSystemAdapter):
    """
    :py:class:`~tardis.adapters.batchsystems.fakebatchsystem.FakeBatchSystemAdapter`
    implements a batch system adapter that mocks the response of a hypothetical
    batch system. It can be used for testing purposes and as a demonstrator
    in workshops and tutorials.

    The mocked response to the :py:meth:`~.get_utilization`, :py:meth:`~.get_allocation`
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

    async def get_utilization(self, drone_uuid: str) -> float:
        """
        Returns the fake utilization according to the configuration of the
        FakeBatchSystem

        :param drone_uuid: Unique identifier of the drone
        :type drone_uuid: str
        :return: Utilization value specified in the FakeBatchSystem configuration
        :rtype: float
        """
        try:
            utilization = self.fake_config.utilization.get_value()
        except AttributeError:
            return self.fake_config.utilization
        else:
            return utilization
