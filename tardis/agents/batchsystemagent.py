from ..interfaces.batchsystemadapter import BatchSystemAdapter
from ..interfaces.batchsystemadapter import MachineStatus
from ..utilities.attributedict import AttributeDict


class BatchSystemAgent(BatchSystemAdapter):
    def __init__(self, batch_system_adapter: BatchSystemAdapter):
        self._batch_system_adapter = batch_system_adapter

    async def disintegrate_machine(self, drone_uuid: str) -> None:
        return await self._batch_system_adapter.disintegrate_machine(drone_uuid)

    async def drain_machine(self, drone_uuid: str) -> None:
        return await self._batch_system_adapter.drain_machine(drone_uuid)

    async def integrate_machine(self, drone_uuid: str) -> None:
        return await self._batch_system_adapter.integrate_machine(drone_uuid)

    async def get_allocation(self, drone_uuid: str) -> float:
        return await self._batch_system_adapter.get_allocation(drone_uuid)

    async def get_machine_status(self, drone_uuid: str) -> MachineStatus:
        return await self._batch_system_adapter.get_machine_status(drone_uuid)

    async def get_utilisation(self, drone_uuid: str) -> float:
        return await self._batch_system_adapter.get_utilisation(drone_uuid)

    @property
    def machine_meta_data_translation_mapping(self) -> AttributeDict:
        return self._batch_system_adapter.machine_meta_data_translation_mapping
