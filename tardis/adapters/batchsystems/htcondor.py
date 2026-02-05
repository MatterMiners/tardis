from ...configuration.configuration import Configuration
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...interfaces.batchsystemadapter import BatchSystemAdapter
from ...interfaces.batchsystemadapter import MachineStatus
from ...interfaces.executor import Executor
from ...utilities.executors.shellexecutor import ShellExecutor
from ...utilities.utils import (
    csv_parser,
    htcondor_cmd_option_formatter,
    htcondor_status_cmd_composer,
)
from ...utilities.asynccachemap import AsyncCacheMap
from ...utilities.attributedict import AttributeDict

from datetime import datetime, timedelta
from functools import partial
from shlex import quote
from types import MappingProxyType
from typing import Iterable
import logging

logger = logging.getLogger("cobald.runtime.tardis.adapters.batchsystem.htcondor")


async def htcondor_get_collectors(
    options: AttributeDict, executor: Executor
) -> list[str]:
    """
    Asynchronously retrieve a list of HTCondor collector machine names.

    Runs ``condor_status -collector -af:t Machine`` (plus any additional formatted
    options) using the provided executor, then parses the tab-delimited output
    to extract and return the list of collector machine names.

    :param options: Additional options for the ``condor_status`` call, such as
        ``{'pool': 'htcondor.example'}``, which will be formatted and appended
        to the command.
    :param executor: Executor used to run the ``condor_status`` command
        asynchronously.
    :return: List of collector machine names.
    """
    class_ads = AttributeDict(Machine="Machine")
    # Add collector query option, copy options since it is mutable
    options = options | {"collector": None}
    cmd = htcondor_status_cmd_composer(
        attributes=class_ads,
        options=options,
    )

    try:
        condor_status = await executor.run_command(cmd)
    except CommandExecutionFailure as cef:
        logger.warning(f"condor_status could not be executed due to {cef}!")
        raise

    return [
        row["Machine"]
        for row in csv_parser(
            input_csv=condor_status.stdout,
            fieldnames=tuple(class_ads.keys()),
            delimiter="\t",
        )
    ]


async def htcondor_get_collector_start_dates(
    options: AttributeDict, executor: Executor
) -> dict[str, datetime]:
    """
    Asynchronously retrieve the master daemon start times from HTCondor for machines
    running a collector daemon as well. Assuming both daemons have a similar start date.
    Due to potential bug/feature in HTCondor, the DaemonStartTime of the Collector can
    not be used directly.
    (see https://www-auth.cs.wisc.edu/lists/htcondor-users/2025-July/msg00092.shtml)

    Runs ``condor_status -master -af:t Machine DaemonStartTime`` (plus any
    additional formatted options) using the provided executor, and parses
    the tab-delimited output into a dictionary.

    :param options: Additional options for the ``condor_status`` call, such as
        ``{'pool': 'htcondor.example'}``, which will be formatted and appended
        to the command.
    :param executor: Executor used to run the ``condor_status`` command
        asynchronously.
    :return: List of master daemon start time for host running a collector as well.
        (in datetime format).
    """
    class_ads = AttributeDict(Machine="Machine", DaemonStartTime="DaemonStartTime")
    htcondor_collectors = await htcondor_get_collectors(options, executor)

    # Add master query option, copy options since it is mutable
    options = options | {"master": None}

    cmd = htcondor_status_cmd_composer(
        attributes=class_ads,
        options=options,
        constraint=" || ".join(f'Machine == "{fqdn}"' for fqdn in htcondor_collectors),
    )

    try:
        condor_status = await executor.run_command(cmd)
    except CommandExecutionFailure as cef:
        logger.warning(f"condor_status could not be executed due to {cef}!")
        raise

    return {
        row["Machine"]: datetime.fromtimestamp(int(row["DaemonStartTime"]))
        for row in csv_parser(
            input_csv=condor_status.stdout,
            fieldnames=tuple(class_ads.keys()),
            delimiter="\t",
        )
        if row["Machine"] in htcondor_collectors
    }


async def htcondor_status_updater(
    options: AttributeDict,
    attributes: AttributeDict,
    executor: Executor,
    cached_data: MappingProxyType,
) -> dict:
    """
    Helper function to call ``condor_status -af`` asynchronously and to translate
    the output into a dictionary.

    If the HTCondor Collector has been running for less than 3600 seconds,
    previously cached status data is used for machines that were already
    available before the restart; otherwise, fresh status data is used.

    :param options: Additional options for the condor_status call. For example
        ``{'pool': 'htcondor.example'}`` will be translated into
        ``condor_status -af ... -pool htcondor.example``
    :param attributes: Additional fields to add to output of the
        ``condor_status -af`` response.
    :param executor: Executor to run the ``condor_status`` command asynchronously.
    :param ro_cached_data: Cached output from previous ``condor_status -af`` call
    :return: Dictionary containing the processed output of the ``condor_status``
        command, possibly merged with cached data depending on collector uptime.
    """
    # copy options, since they are mutable
    options = AttributeDict(**options)

    collector_start_dates = await htcondor_get_collector_start_dates(options, executor)

    threshold = timedelta(seconds=3600)
    now = datetime.now()

    earliest_start_date = min(collector_start_dates.values())
    latest_start_date = max(collector_start_dates.values())

    if (now - earliest_start_date) < threshold:
        # If all collectors have been running for less than 3600 seconds,
        # use cached status for machines that were already available before the
        # restart and update it with fresh data if available.
        htcondor_status = cached_data.copy()

    elif (now - latest_start_date) < threshold:
        # If any collector has been running for more than 3600 seconds, use the oldest
        # available one.
        htcondor_status = {}
        oldest_collector = min(collector_start_dates, key=collector_start_dates.get)
        options.pool = oldest_collector

    else:
        # Repopulate HTCondor status
        htcondor_status = {}

    cmd = htcondor_status_cmd_composer(
        attributes=attributes,
        options=options,
        constraint="PartitionableSlot=?=True",
    )

    try:
        logger.debug(f"HTCondor status update is running. Command: {cmd}")
        condor_status = await executor.run_command(cmd)

        for row in csv_parser(
            input_csv=condor_status.stdout,
            fieldnames=tuple(attributes.keys()),
            delimiter="\t",
            replacements=dict(undefined=None),
        ):
            status_key = row["TardisDroneUuid"] or row["Machine"].split(".")[0]
            htcondor_status[status_key] = row
    except CommandExecutionFailure as cef:
        logger.warning(f"condor_status could not be executed due to {cef}!")
        raise
    else:
        logger.debug("HTCondor status update finished.")
        return htcondor_status


class HTCondorAdapter(BatchSystemAdapter):
    """
    :py:class:`~tardis.adapters.batchsystems.htcondor.HTCondorAdapter` implements
    the TARDIS interface to dynamically integrate and manage opportunistic resources
    with the HTCondor Batch System.
    """

    def __init__(self):
        config = Configuration()
        self.ratios = config.BatchSystem.ratios
        self._executor = getattr(config.BatchSystem, "executor", ShellExecutor())

        try:
            self.htcondor_options = config.BatchSystem.options
        except AttributeError:
            self.htcondor_options = AttributeDict()

        attributes = dict(
            Machine="Machine",
            Name="Name",
            State="State",
            Activity="Activity",
            TardisDroneUuid="TardisDroneUuid",
        )
        # Escape htcondor expressions and add them to attributes
        attributes.update({key: quote(value) for key, value in self.ratios.items()})

        self._htcondor_status = AsyncCacheMap(
            update_coroutine=partial(
                htcondor_status_updater,
                self.htcondor_options,
                attributes,
                self._executor,
            ),
            max_age=config.BatchSystem.max_age * 60,
            provide_cache=True,
        )

    async def disintegrate_machine(self, drone_uuid: str) -> None:
        """
        HTCondor does not require any specific disintegration procedure.

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        """
        return

    async def drain_machine(self, drone_uuid: str) -> None:
        """
        Drain a machine in the HTCondor batch system, which means that no new
        jobs will be accepted

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        """
        await self._htcondor_status.update_status()
        try:
            slot_name = self._htcondor_status[drone_uuid]["Name"]
        except KeyError:
            return

        options_string = htcondor_cmd_option_formatter(self.htcondor_options)

        if options_string:
            cmd = f"condor_drain {options_string} -graceful {slot_name}"
        else:
            cmd = f"condor_drain -graceful {slot_name}"

        try:
            await self._executor.run_command(cmd)
        except CommandExecutionFailure as cef:
            if cef.exit_code == 1:
                # exit code 1: HTCondor can't connect to StartD of Drone
                # https://github.com/htcondor/htcondor/blob/master/src/condor_tools/drain.cpp  # noqa: B950
                logger.warning(
                    f"Draining failed with: {str(cef)}. Probably drone {drone_uuid}"
                    " is not available or already drained."
                )
                return
            logger.critical(f"Draining failed with: {str(cef)}.")
            raise cef

    async def integrate_machine(self, drone_uuid: str) -> None:
        """
        HTCondor does not require any specific integration procedure

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        """
        return None

    async def get_resource_ratios(self, drone_uuid: str) -> Iterable[float]:
        """
        Get the ratio of requested over total resources (CPU, Memory, Disk, etc.)
        for a worker node in HTCondor according to the HTCondor expressions
        defined in the adapter configuration.

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        :return: Iterable of float containing the ratios
        """
        await self._htcondor_status.update_status()
        try:
            htcondor_status = self._htcondor_status[drone_uuid]
            return [
                float(value)
                for key, value in htcondor_status.items()
                if key in self.ratios.keys()
            ]
        except (KeyError, ValueError, TypeError):
            return []

    async def get_allocation(self, drone_uuid: str) -> float:
        """
        Get the allocation of a worker node in HTCondor, which is defined as maximum
        of the ratios of requested over total resources (CPU, Memory, Disk, etc.).

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        :return: The allocation of a worker node as described above.
        """
        return max(await self.get_resource_ratios(drone_uuid), default=0.0)

    async def get_machine_status(self, drone_uuid: str) -> MachineStatus:
        """
        Get the status of a worker node in HTCondor (Available, Draining,
        Drained, NotAvailable)

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        :return: The machine status in HTCondor (Available, Draining, Drained,
            NotAvailable)
        """
        status_mapping = {
            ("Unclaimed", "Idle"): MachineStatus.Available,
            ("Drained", "Retiring"): MachineStatus.Draining,
            ("Drained", "Idle"): MachineStatus.Drained,
            ("Owner", "Idle"): MachineStatus.NotAvailable,
        }

        await self._htcondor_status.update_status()
        try:
            machine_status = self._htcondor_status[drone_uuid]
        except KeyError:
            return MachineStatus.NotAvailable
        else:
            return status_mapping.get(
                (machine_status["State"], machine_status["Activity"]),
                MachineStatus.NotAvailable,
            )

    async def get_utilisation(self, drone_uuid: str) -> float:
        """
        Get the utilisation of a worker node in HTCondor, which is defined as
        minimum of the ratios of requested over total resources
        (CPU, Memory, Disk, etc.).

        :param drone_uuid: Uuid of the worker node, for some sites corresponding
            to the host name of the drone.
        :return: The utilisation of a worker node as described above.
        """
        return min(await self.get_resource_ratios(drone_uuid), default=0.0)

    @property
    def machine_meta_data_translation_mapping(self) -> AttributeDict:
        """
        The machine metadata translation mapping is used to translate units of
        the machine metadata in ``TARDIS`` to values expected by the
        HTCondor batch system adapter.

        :return: Machine metadata translation mapping
        """
        return AttributeDict(Cores=1, Memory=1024, Disk=1024 * 1024)
