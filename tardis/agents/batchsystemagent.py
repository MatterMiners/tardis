from ..interfaces.batchsystemadapter import BatchSystemAdapter


class BatchSystemAgent(BatchSystemAdapter):
    def __init__(self, batch_system_adapter):
        self._batch_system_adapter = batch_system_adapter

    async def disintegrate_machine(self, dns_name):
        return await self._batch_system_adapter.disintegrate_machine(dns_name)

    async def drain_machine(self, dns_name):
        return await self._batch_system_adapter.drain_machine(dns_name)

    async def integrate_machine(self, dns_name):
        return await self._batch_system_adapter.integrate_machine(dns_name)

    async def get_allocation(self, dns_name):
        return await self._batch_system_adapter.get_allocation(dns_name)

    async def get_machine_status(self, dns_name=None):
        return await self._batch_system_adapter.get_machine_status(dns_name)

    async def get_utilization(self, dns_name):
        return await self._batch_system_adapter.get_utilization(dns_name)
