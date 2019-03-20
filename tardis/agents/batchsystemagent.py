from ..interfaces.batchsystemadapter import BatchSystemAdapter


class BatchSystemAgent(BatchSystemAdapter):
    def __init__(self, batch_system_adapter):
        self._batch_system_adapter = batch_system_adapter

    async def disintegrate_machine(self, drone_uuid):
        return await self._batch_system_adapter.disintegrate_machine(drone_uuid)

    async def drain_machine(self, drone_uuid):
        return await self._batch_system_adapter.drain_machine(drone_uuid)

    async def integrate_machine(self, drone_uuid):
        return await self._batch_system_adapter.integrate_machine(drone_uuid)

    async def get_allocation(self, drone_uuid):
        return await self._batch_system_adapter.get_allocation(drone_uuid)

    async def get_machine_status(self, drone_uuid):
        return await self._batch_system_adapter.get_machine_status(drone_uuid)

    async def get_utilization(self, drone_uuid):
        return await self._batch_system_adapter.get_utilization(drone_uuid)
