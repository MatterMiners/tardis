"""SLURM Batch system Adapter"""

import logging
import os

from functools import partial

from typing import Iterable

from ...configuration.configuration import Configuration
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...interfaces.batchsystemadapter import BatchSystemAdapter
from ...interfaces.batchsystemadapter import MachineStatus
from ...utilities.utils import async_run_command
from ...utilities.utils import slurm_cmd_option_formatter
from ...utilities.utils import slurm_csv_parser
from ...utilities.asynccachemap import AsyncCacheMap
from ...utilities.attributedict import AttributeDict


async def slurm_status_updater(
    options: AttributeDict, attributes: AttributeDict
) -> dict:
    """
    Slurm status update.

    :param options: Additional parameters for the ``sinfo`` command
    :type options: AttributeDict
    :param attributes: Formatting options for ``sinfo``
    :type attributes: AttributeDict
    :return: Dictionary containing the output of the ``sinfo`` command
    :rtype: dict
    """

    options_string = slurm_cmd_option_formatter(options)

    # Needlessly complicated (Rust, where art thou??)
    attributes_string = ",".join([str(x) for x in attributes.values()])

    cmd = f'sinfo --Format="{attributes_string}" -e --noheader'
    #  cmd = f'sinfo --Format="{attributes_string}" -e --noheader -r'

    if options_string:
        cmd = f"{cmd} {options_string}"

    slurm_status = {}

    try:
        logging.debug(f"SLURM status update is running. Command: {cmd}")
        status = await async_run_command(cmd)

        for row in slurm_csv_parser(
            slurm_input=status,
            fieldnames=tuple(attributes.keys()),
            delimiter=" ",
            replacements=dict(undefined=None),
        ):
            row["CPUs"] = list(map(float, row["CPUs"].split("/")))
            # Convert to float because we want to do some math!
            row["TotalMem"] = float(row["TotalMem"])
            try:
                row["FreeMem"] = row["TotalMem"] - float(row["AllocMem"])
            except ValueError:
                # Not sure what it should be.
                #  row["FreeMem"] = 0.0
                row["FreeMem"] = row["TotalMem"]
            machine = row["Machine"]
            cmd = f'sinfo -n {machine} --format="%f" --noheader'
            stream = os.popen(cmd)
            status_key = stream.read().strip()

            # wat?
            if status_key is not None and status_key:
                slurm_status[status_key] = row

    except CommandExecutionFailure as ex:
        logging.error("SLURM's sinfo could not be executed!")
        logging.error(str(ex))
        raise
    else:
        logging.debug("SLURM status update finished.")
        return slurm_status


class SlurmAdapter(BatchSystemAdapter):
    """
    :py:class:`~tardis.adapters.batchsystems.slurm.SlurmAdapter` implements the
    TARDIS interface to dynamically integrate and manage opportunistic resources
    with the SLURM Batch System.
    """

    def __init__(self):
        config = Configuration()

        try:
            self.slurm_options = config.BatchSystem.options
        except AttributeError:
            self.slurm_options = {}

        attributes = {
            "State": "statelong",
            "CPUs": "cpusstate",
            "AllocMem": "allocmem",
            "TotalMem": "memory",
            "Features": "features",
            "Machine": "nodehost",
        }

        self._slurm_status = AsyncCacheMap(
            update_coroutine=partial(
                slurm_status_updater, self.slurm_options, attributes
            ),
            max_age=config.BatchSystem.max_age * 60,
        )

    async def disintegrate_machine(self, drone_uuid: str) -> None:
        """
        SLURM does not require any specific disintegration procedure (at least
        in Freiburg).

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
        to the host name of the drone.
        :type drone_uuid: str
        :return: None
        """
        return

    async def drain_machine(self, drone_uuid: str) -> None:
        """
        Drain a machine in the SLURM batch system, which means that no new
        jobs will be accepted

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
        to the host name of the drone.
        :type drone_uuid: str
        :return: None
        """
        await self._slurm_status.update_status()
        try:
            machine = self._slurm_status[drone_uuid]["Machine"]
        except KeyError:
            return

        cmd = f"scontrol update NodeName={machine} State=DRAIN Reason='COBalD/TARDIS'"

        try:
            return await async_run_command(cmd)
        except CommandExecutionFailure as ex:
            raise ex

    async def integrate_machine(self, drone_uuid: str) -> None:
        """
        SLURM does not require any specific integration procedure (if the Drones
        take care of it themselves)

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
        to the host name of the drone.
        :type drone_uuid: str
        :return: None
        """
        return None

    async def get_resource_ratios(self, drone_uuid: str) -> Iterable[float]:
        """
        Get the ratio of requested over total resources (CPU, Memory, Disk,
        etc.) for a worker node in HTCondor according to the HTCondor
        expressions defined in the adapter configuration.

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
        to the host name of the drone.
        :type drone_uuid: str
        :return: Iterable of float containing the ratios
        :rtype: Iterable[float]
        """

        # TODO: We can't define formulas such as the ones possible in HTCondor.
        # Therefore we need to to some math here!
        await self._slurm_status.update_status()
        try:
            slurm_status = self._slurm_status[drone_uuid]
        except KeyError:
            return {}
        else:
            return (
                (slurm_status["CPUs"][3] - slurm_status["CPUs"][1])
                / slurm_status["CPUs"][3],
                (slurm_status["TotalMem"] - slurm_status["FreeMem"])
                / slurm_status["TotalMem"],
            )

    async def get_allocation(self, drone_uuid: str) -> float:
        """
        Get the allocation of a worker node in SLURM, which is defined as
        maximum of the ratios of requested over total resources (CPU, Memory,
        Disk, etc.).

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
        to the host name of the drone.
        :type drone_uuid: str
        :return: The allocation of a worker node as described above.
        :rtype: float
        """
        return max(await self.get_resource_ratios(drone_uuid), default=0.0)

    async def get_machine_status(self, drone_uuid: str) -> MachineStatus:
        """
        Get the status of a worker node in SLURM (Available, Draining,
        Drained, NotAvailable)

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
        to the host name of the drone.
        :type drone_uuid: str
        :return: The machine status in SLURM (Available, Draining, Drained,
        NotAvailable)
        :rtype: MachineStatus
        """

        # '*' means it didn't respond for a while
        status_mapping = {
            "allocated": MachineStatus.Available,
            "allocated+": MachineStatus.Available,
            "mixed": MachineStatus.Available,
            "idle": MachineStatus.Available,
            "completing": MachineStatus.Draining,
            "completing+": MachineStatus.Draining,
            "draining": MachineStatus.Draining,
            "down": MachineStatus.Drained,
            "down*": MachineStatus.Drained,
            "drained": MachineStatus.Drained,
            "drained*": MachineStatus.Drained,
            "fail": MachineStatus.Drained,
            "failing": MachineStatus.Drained,
            "future": MachineStatus.Drained,
            "maint": MachineStatus.Drained,
            "reboot": MachineStatus.Drained,
            "power_down": MachineStatus.Drained,
            "powering_down": MachineStatus.Drained,
            "reserved": MachineStatus.Drained,
            "unknown": MachineStatus.NotAvailable,
            "power_up": MachineStatus.NotAvailable,
        }

        await self._slurm_status.update_status()
        try:
            machine_status = self._slurm_status[drone_uuid]
        except KeyError:
            return MachineStatus.NotAvailable
        else:
            return status_mapping.get(
                machine_status["State"], MachineStatus.NotAvailable
            )

    async def get_utilization(self, drone_uuid: str) -> float:
        """
        Get the utilization of a worker node in Slurm, which is defined as
        minimum of the ratios of requested over total resources (CPU, Memory,
        Disk, etc.).

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
        to the host name of the drone.
        :type drone_uuid: str
        :return: The utilization of a worker node as described above.
        :rtype: float
        """
        return min(await self.get_resource_ratios(drone_uuid), default=0.0)
