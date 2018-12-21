from ..configuration.configuration import Configuration
from ..exceptions.tardisexceptions import AsyncRunCommandFailure
from ..interfaces.batchsystemadapter import BatchSystemAdapter
from ..interfaces.batchsystemadapter import MachineStatus
from ..utilities.utils import async_run_command
from ..utilities.asynccachemap import AsyncCacheMap

from io import StringIO
from shlex import quote
import csv
import logging


async def htcondor_status_updater():
    attributes = dict(Machine='Machine', State='State', Activity='Activity')
    # Escape htcondor expressions and add them to attributes
    attributes.update({key: quote(value) for key, value in Configuration().BatchSystem.ratios.items()})
    attributes_string = " ".join(attributes.values())
    cmd = f'condor_status -af:t {attributes_string} -constraint PartitionableSlot=?=True'

    htcondor_status = {}

    try:
        condor_status = await async_run_command(cmd)
        with StringIO(condor_status) as csv_input:
            cvs_reader = csv.DictReader(csv_input, fieldnames=tuple(attributes.keys()), delimiter='\t')
            for row in cvs_reader:
                htcondor_status[row['Machine'].split('.')[0]] = row
    except AsyncRunCommandFailure as ex:
        logging.error("condor_status could not be executed!")
        logging.error(str(ex))
    else:
        return htcondor_status


class HTCondorAdapter(BatchSystemAdapter):
    def __init__(self):
        config = Configuration()
        self._htcondor_status = AsyncCacheMap(update_coroutine=htcondor_status_updater,
                                              max_age=config.BatchSystem.max_age * 60)
        self.ratios = config.BatchSystem.ratios

    async def disintegrate_machine(self, dns_name):
        """
        HTCondor does not require any specific disintegration procedure. Other batchsystems probably do.
        :param dns_name: DNS name of the worker node
        :return: None
        """
        return None

    async def drain_machine(self, dns_name):
        await self._htcondor_status.update_status()
        try:
            machine = self._htcondor_status[dns_name]['Machine']
        except KeyError:
            return
        else:
            cmd = f'condor_drain -graceful {machine}'
            return await async_run_command(cmd)

    async def integrate_machine(self, dns_name):
        """
        HTCondor does not require any specific integration procedure. Other batchsystems probably do.
        :param dns_name: DNS name of the worker node
        :return: None
        """
        return None

    async def get_resource_ratios(self, dns_name):
        await self._htcondor_status.update_status()
        try:
            htcondor_status = self._htcondor_status[dns_name]
        except KeyError:
            return {}
        else:
            return (float(value) for key, value in htcondor_status.items() if key in self.ratios.keys())

    async def get_allocation(self, dns_name):
        return max(await self.get_resource_ratios(dns_name), default=0.)

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
        return min(await self.get_resource_ratios(dns_name), default=0.)
