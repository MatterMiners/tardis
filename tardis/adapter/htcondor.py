from ..exceptions.tardisexceptions import AsyncRunCommandFailure
from ..interfaces.batchsystemadapter import BatchSystemAdapter
from ..interfaces.batchsystemadapter import MachineStatus
from ..utilities.utils import async_run_command
from ..utilities.asynccachemap import AsyncCacheMap


import json
import logging


async def htcondor_status_updater():
    cmd = 'condor_status'
    args = ['-attributes',
            'Machine,State,Activity,TotalSlotMemory,Memory,TotalCpus,TotalSlotCpus,Cpus,TotalSlotDisk,Disk',
            '-json', '-constraint', 'PartitionableSlot=?=True']
    htcondor_status = {}
    try:
        for entry in json.loads(await async_run_command(cmd, *args)):
            htcondor_status.setdefault(entry['Machine'].split('.')[0], []).append(entry)
    except AsyncRunCommandFailure as ex:
        logging.error("condor_status could not be executed!")
        logging.error(str(ex))
    finally:
        return htcondor_status


class HTCondorAdapter(BatchSystemAdapter):
    def __init__(self):
        self._htcondor_status = AsyncCacheMap(update_coroutine=htcondor_status_updater, max_age=60)

    async def disintegrate_machine(self, dns_name):
        """
        HTCondor does not require any specific disintegration procedure. Other batchsystems probably do.
        :param dns_name: DNS name of the worker node
        :return: None
        """
        return None

    async def drain_machine(self, dns_name):
        await self._htcondor_status.update_status()
        machine = self._htcondor_status[dns_name]['Machine']
        cmd = 'condor_drain'
        args = ('-graceful', machine)
        return await async_run_command(cmd, *args)

    async def integrate_machine(self, dns_name):
        """
        HTCondor does not require any specific integration procedure. Other batchsystems probably do.
        :param dns_name: DNS name of the worker node
        :return: None
        """
        return None

    async def get_resource_ratio(self, dns_name):
        await self._htcondor_status.update_status()
        htcondor_status = self._htcondor_status[dns_name]

        ratio_functions = [lambda: (htcondor_status['TotalSlotCpus'] - htcondor_status['Cpus']) / htcondor_status[
                               'TotalSlotCpus'],
                           lambda: (htcondor_status['TotalSlotMemory'] - htcondor_status['Memory']) / htcondor_status[
                               'TotalSlotMemory'],
                           lambda: (htcondor_status['TotalSlotDisk'] - htcondor_status['Disk']) / htcondor_status[
                               'TotalSlotDisk'],
                           ]

        return (self.handle_zero_division_error(ratio_function) for ratio_function in ratio_functions)

    async def get_allocation(self, dns_name):
        return max(await self.get_resource_ratio(dns_name))

    async def get_machine_status(self, dns_name=None):
        status_mapping = {('Unclaimed', 'Idle'): MachineStatus.Available,
                          ('Drained', 'Retiring'): MachineStatus.Draining,
                          ('Drained', 'Idle'): MachineStatus.Drained,
                          ('Owner', 'Idle'): MachineStatus.NotAvailable}

        await self._htcondor_status.update_status()
        try:
            machine_status = self._htcondor_status[dns_name]
        except KeyError:
            return MachineStatus.NotAvailable
        else:
            return status_mapping.get((machine_status['State'], machine_status['Activity']), MachineStatus.NotAvailable)

    async def get_utilization(self, dns_name):
        return min(await self.get_resource_ratio(dns_name))

    @staticmethod
    def handle_zero_division_error(ratio_function, default_return_value=0):
        try:
            return ratio_function()
        except ZeroDivisionError:
            return default_return_value
