from ...configuration.configuration import Configuration
from ...exceptions.tardisexceptions import AsyncRunCommandFailure
from ...interfaces.batchsystemadapter import BatchSystemAdapter
from ...interfaces.batchsystemadapter import MachineStatus
from ...utilities.utils import async_run_command
from ...utilities.utils import htcondor_cmd_option_formatter
from ...utilities.utils import htcondor_csv_parser
from ...utilities.asynccachemap import AsyncCacheMap

from functools import partial
from shlex import quote
import logging


async def htcondor_status_updater(options, attributes):
    attributes_string = f'-af:t {" ".join(attributes.values())}'

    options_string = htcondor_cmd_option_formatter(options)

    cmd = f"condor_status {attributes_string} -constraint PartitionableSlot=?=True"

    if options_string:
        cmd = f"{cmd} {options_string}"

    htcondor_status = {}

    try:
        logging.debug("HTCondor status update is running.")
        condor_status = await async_run_command(cmd)
        for row in htcondor_csv_parser(htcondor_input=condor_status, fieldnames=tuple(attributes.keys()),
                                       delimiter='\t', replacements=dict(undefined=None)):
            status_key = row['TardisDroneUuid'] or row['Machine'].split('.')[0]
            htcondor_status[status_key] = row

    except AsyncRunCommandFailure as ex:
        logging.error("condor_status could not be executed!")
        logging.error(str(ex))
    else:
        logging.debug("HTCondor status update finished.")
        return htcondor_status


class HTCondorAdapter(BatchSystemAdapter):
    def __init__(self):
        config = Configuration()
        self.ratios = config.BatchSystem.ratios

        try:
            self.htcondor_options = config.BatchSystem.options
        except AttributeError:
            self.htcondor_options = {}

        attributes = dict(Machine='Machine', State='State', Activity='Activity', TardisDroneUuid='TardisDroneUuid')
        # Escape htcondor expressions and add them to attributes
        attributes.update({key: quote(value) for key, value in self.ratios.items()})

        self._htcondor_status = AsyncCacheMap(update_coroutine=partial(htcondor_status_updater, self.htcondor_options,
                                                                       attributes),
                                              max_age=config.BatchSystem.max_age * 60)

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

        options_string = htcondor_cmd_option_formatter(self.htcondor_options)

        if options_string:
            cmd = f"condor_drain {options_string} -graceful {machine}"
        else:
            cmd = f"condor_drain -graceful {machine}"

        try:
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
