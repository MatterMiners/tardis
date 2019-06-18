from tardis.configuration.configuration import Configuration
from tardis.interfaces.batchsystemadapter import BatchSystemAdapter
from tardis.interfaces.batchsystemadapter import MachineStatus


class FakeBatchSystemAdapter(BatchSystemAdapter):
    def __init__(self):
        config = Configuration()
        self.fake_config = config.BatchSystem
        self._drained_machines = {}

    async def disintegrate_machine(self, drone_uuid):
        return

    async def drain_machine(self, drone_uuid):
        self._drained_machines[drone_uuid] = MachineStatus.Drained
        return

    async def integrate_machine(self, drone_uuid):
        return

    async def get_allocation(self, drone_uuid):
        return self.fake_config.allocation

    async def get_machine_status(self, drone_uuid):
        try:
            machine_status = self._drained_machines[drone_uuid]
        except KeyError:
            return getattr(MachineStatus, self.fake_config.machine_status)
        else:
            return machine_status

    async def get_utilization(self, drone_uuid):
        return self.fake_config.utilization
