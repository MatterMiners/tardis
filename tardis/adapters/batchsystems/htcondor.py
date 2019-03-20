from tardis.configuration.configuration import Configuration
from tardis.exceptions.tardisexceptions import AsyncRunCommandFailure
from tardis.interfaces.batchsystemadapter import BatchSystemAdapter
from tardis.interfaces.batchsystemadapter import MachineStatus
from tardis.utilities.utils import async_run_command
from tardis.utilities.asynccachemap import AsyncCacheMap

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
        logging.debug("HTCondor status update is running.")
        condor_status = await async_run_command(cmd)
        with StringIO(condor_status) as csv_input:
            cvs_reader = csv.DictReader(csv_input, fieldnames=tuple(attributes.keys()), delimiter='\t')
            for row in cvs_reader:
                htcondor_status[row['Machine'].split('.')[0]] = row
    except AsyncRunCommandFailure as ex:
        logging.error("condor_status could not be executed!")
        logging.error(str(ex))
    else:
        logging.debug("HTCondor status update finished.")
        return htcondor_status


class HTCondorAdapter(BatchSystemAdapter):
    def __init__(self):
        config = Configuration()
        self._htcondor_status = AsyncCacheMap(update_coroutine=htcondor_status_updater,
                                              max_age=config.BatchSystem.max_age * 60)
        self.ratios = config.BatchSystem.ratios

    async def disintegrate_machine(self, drone_uuid):
        """
        HTCondor does not require any specific disintegration procedure. Other batchsystems probably do.
        :param drone_uuid: Uuid of the worker node, for some sites corresponding to the host name of drone
        :return: None
        """
        return None

    async def drain_machine(self, drone_uuid):
        await self._htcondor_status.update_status()
        try:
            machine = self._htcondor_status[drone_uuid]['Machine']
        except KeyError:
            return
        try:
            cmd = f'condor_drain -graceful {machine}'
            return await async_run_command(cmd)
        except AsyncRunCommandFailure as ex:
            if ex.error_code == 1:
                # exit code 1: HTCondor can't connect to StartD of Drone
                # https://github.com/htcondor/htcondor/blob/master/src/condor_tools/drain.cpp
                logging.debug("Drone %s is not in HTCondor anymore." % drone_uuid)
                return
            raise ex

    async def integrate_machine(self, drone_uuid):
        """
        HTCondor does not require any specific integration procedure. Other batchsystems probably do.
        :param drone_uuid: DNS name of the worker node
        :return: None
        """
        return None

    async def get_resource_ratios(self, drone_uuid):
        await self._htcondor_status.update_status()
        try:
            htcondor_status = self._htcondor_status[drone_uuid]
        except KeyError:
            return {}
        else:
            return (float(value) for key, value in htcondor_status.items() if key in self.ratios.keys())

    async def get_allocation(self, drone_uuid):
        return max(await self.get_resource_ratios(drone_uuid), default=0.)

    async def get_machine_status(self, drone_uuid):
        status_mapping = {('Unclaimed', 'Idle'): MachineStatus.Available,
                          ('Drained', 'Retiring'): MachineStatus.Draining,
                          ('Drained', 'Idle'): MachineStatus.Drained,
                          ('Owner', 'Idle'): MachineStatus.NotAvailable}

        await self._htcondor_status.update_status()
        try:
            machine_status = self._htcondor_status[drone_uuid]
        except KeyError:
            return MachineStatus.NotAvailable
        else:
            return status_mapping.get((machine_status['State'], machine_status['Activity']), MachineStatus.NotAvailable)

    async def get_utilization(self, drone_uuid):
        return min(await self.get_resource_ratios(drone_uuid), default=0.)
