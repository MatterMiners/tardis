from ..interfaces.batchsystemadapter import BatchSystemAdapter


class BatchSystemAgent(BatchSystemAdapter):
    def __init__(self, batch_system_adapter):
        self._batch_system_adapter = batch_system_adapter

    async def integrate_machine(self, dns_name):
        return await self._batch_system_adapter.integrate_machine(dns_name)

    def get_allocation(self, dns_name):
        return self._batch_system_adapter.get_allocation(dns_name)

    def get_machine_status(self, dns_name=None):
        return self._batch_system_adapter.get_machine_status(dns_name)

    def get_utilization(self, dns_name):
        return self._batch_system_adapter.get_utilization(dns_name)
