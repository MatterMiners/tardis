from ..exceptions.tardisexceptions import AsyncRunCommandFailure
from ..interfaces.batchsystemadapter import BatchSystemAdapter
from ..interfaces.batchsystemadapter import MachineActivities
from ..utilities.utils import async_run_command
from ..utilities.asynccachemap import AsyncCacheMap


import json
import logging


async def htcondor_status_updater():
    cmd = 'condor_status'
    args = ['-attributes', 'Machine,Activity,TotalSlotMemory,Memory,TotalCpus,TotalSlotCpus,Cpus,TotalSlotDisk,Disk',
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
        self._htcondor_status = AsyncCacheMap(update_coroutine=htcondor_status_updater, max_age=60 * 15)

    async def integrate_machine(self, dns_name):
        """
        HTCondor does not require any specific integration procedure. Other batchsystems probably do.
        :param dns_name: DNS name of the worker node
        :return: None
        """
        return None

    def get_resource_ratio(self, dns_name):
        htcondor_status = self._htcondor_status[dns_name]

        ratio_functions = [lambda: (htcondor_status['TotalSlotCpus'] - htcondor_status['Cpus']) / htcondor_status[
                               'TotalSlotCpus'],
                           lambda: (htcondor_status['TotalSlotMemory'] - htcondor_status['Memory']) / htcondor_status[
                               'TotalSlotMemory'],
                           lambda: (htcondor_status['TotalSlotDisk'] - htcondor_status['Disk']) / htcondor_status[
                               'TotalSlotDisk'],
                           ]

        return (self.handle_zero_division_error(ratio_function) for ratio_function in ratio_functions)

    def get_allocation(self, dns_name):
        return max(self.get_resource_ratio(dns_name))

    def get_machine_status(self, dns_name=None):
        try:
            activity = self._htcondor_status[dns_name]['Activity']
        except KeyError:
            return MachineActivities.NotIntegrated
        else:
            return getattr(MachineActivities, activity)

    def get_utilization(self, dns_name):
        return min(self.get_resource_ratio(dns_name))

    @staticmethod
    def handle_zero_division_error(ratio_function, default_return_value=0):
        try:
            return ratio_function()
        except ZeroDivisionError:
            return default_return_value
