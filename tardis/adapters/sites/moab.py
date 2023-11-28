from ...exceptions.executorexceptions import CommandExecutionFailure
from ...exceptions.tardisexceptions import TardisError
from ...exceptions.tardisexceptions import TardisTimeout
from ...exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ...interfaces.executor import Executor
from ...interfaces.siteadapter import ResourceStatus
from ...interfaces.siteadapter import SiteAdapter
from ...utilities.staticmapping import StaticMapping
from ...utilities.asyncbulkcall import AsyncBulkCall
from ...utilities.attributedict import AttributeDict
from ...utilities.executors.shellexecutor import ShellExecutor
from ...utilities.utils import (
    convert_to,
    drone_environment_to_str,
    submit_cmd_option_formatter,
)

from asyncio import TimeoutError
from contextlib import contextmanager
from functools import partial
from typing import Iterable, Mapping, Tuple

import asyncssh
import logging
import warnings
from xml.dom import minidom

logger = logging.getLogger("cobald.runtime.tardis.adapters.sites.moab")


async def showq(
    *resource_attributes: Tuple[AttributeDict, ...], executor: Executor
) -> Iterable[Mapping]:
    showq_active_cmd = "showq --xml -w user=${USER}"
    showq_completed_cmd = "showq -c --xml -w user=${USER}"
    logger.debug("Moab status update is running.")
    combined_response_stdout = ""
    for cmd in (showq_active_cmd, showq_completed_cmd):
        response = await executor.run_command(cmd)
        combined_response_stdout += response.stdout
    # combine two XML outputs to one
    xml_output = minidom.parseString(
        combined_response_stdout.replace("\n", "").replace("</Data><Data>", "")
    )
    xml_jobs_list = xml_output.getElementsByTagName("queue")
    # parse XML output
    moab_resource_status = {}
    for queue in xml_jobs_list:
        queue_jobs_list = queue.getElementsByTagName("job")
        for line in queue_jobs_list:
            moab_resource_status[line.attributes["JobID"].value] = {
                "JobID": line.attributes["JobID"].value,
                "State": line.attributes["State"].value,
            }
    logger.debug("Moab status update completed")

    return (
        moab_resource_status.get(
            str(resource.remote_resource_uuid),
            # assume that jobs that do not show up (anymore) in squeue have
            # State Completed (Deleted)
            {
                "State": "Completed",
            },
        )
        for resource in resource_attributes
    )


class MoabAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str):
        self._machine_type = machine_type
        self._site_name = site_name

        try:
            self._startup_command = self.machine_type_configuration.StartupCommand
        except AttributeError:
            if not hasattr(self.configuration, "StartupCommand"):
                raise
            warnings.warn(
                "StartupCommand has been moved to the machine_type_configuration!",
                DeprecationWarning,
                stacklevel=2,
            )
            self._startup_command = self.configuration.StartupCommand

        self._executor = getattr(self.configuration, "executor", ShellExecutor())

        key_translator = StaticMapping(
            remote_resource_uuid="JobID", resource_status="State"
        )

        # see job state codes at https://computing.llnl.gov/tutorials/moab/#JobStates
        translator_functions = StaticMapping(
            State=lambda x, translator=StaticMapping(
                BatchHold=ResourceStatus.Stopped,
                Canceling=ResourceStatus.Running,
                CANCELLED=ResourceStatus.Deleted,
                Completed=ResourceStatus.Deleted,
                COMPLETED=ResourceStatus.Deleted,
                COMPLETING=ResourceStatus.Running,
                Deffered=ResourceStatus.Booting,
                Depend=ResourceStatus.Error,
                Dependency=ResourceStatus.Error,
                FAILED=ResourceStatus.Error,
                Idle=ResourceStatus.Booting,
                JobHeldUser=ResourceStatus.Stopped,
                Migrated=ResourceStatus.Booting,
                NODE_FAIL=ResourceStatus.Error,
                NotQueued=ResourceStatus.Error,
                PENDING=ResourceStatus.Booting,
                Priority=ResourceStatus.Booting,
                Removed=ResourceStatus.Deleted,
                Resources=ResourceStatus.Booting,
                Running=ResourceStatus.Running,
                RUNNING=ResourceStatus.Running,
                Staging=ResourceStatus.Booting,
                Starting=ResourceStatus.Booting,
                Suspended=ResourceStatus.Stopped,
                SUSPENDED=ResourceStatus.Stopped,
                SystemHold=ResourceStatus.Stopped,
                TimeLimit=ResourceStatus.Deleted,
                TIMEOUT=ResourceStatus.Deleted,
                UserHold=ResourceStatus.Stopped,
                Vacated=ResourceStatus.Deleted,
            ): translator[x],
            JobID=int,
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=translator_functions,
        )

        bulk_size = getattr(self.configuration, "bulk_size", 100)
        bulk_delay = getattr(self.configuration, "bulk_delay", 1.0)

        self._showq = AsyncBulkCall(
            partial(showq, executor=self._executor),
            size=bulk_size,
            delay=bulk_delay,
        )

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        msub_cmdline_option_string = self.msub_cmdline_options(
            resource_attributes.drone_uuid,
            resource_attributes.obs_machine_meta_data_translation_mapping,
        )
        request_command = f"msub {msub_cmdline_option_string} {self._startup_command}"
        result = await self._executor.run_command(request_command)
        logger.debug(f"{self.site_name} servers create returned {result}")

        remote_resource_uuid = int(result.stdout)

        return AttributeDict(
            remote_resource_uuid=remote_resource_uuid,
            resource_status=ResourceStatus.Booting,
        )

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        return self.handle_response(await self._showq(resource_attributes))

    async def terminate_resource(self, resource_attributes: AttributeDict) -> None:
        request_command = f"canceljob {resource_attributes.remote_resource_uuid}"
        try:
            response = await self._executor.run_command(request_command)
        except CommandExecutionFailure as cf:
            if cf.exit_code == 1:
                logger.warning(
                    f"{self.site_name} servers terminate returned {cf.stdout}."
                    "Potentially already terminated."
                )
            else:
                raise cf
        else:
            logger.debug(f"{self.site_name} servers terminate returned {response}")

    async def stop_resource(self, resource_attributes: AttributeDict) -> None:
        logger.debug("MOAB jobs cannot be stopped gracefully. Terminating instead.")
        await self.terminate_resource(resource_attributes)

    def msub_cmdline_options(self, drone_uuid, machine_meta_data_translation_mapping):
        sbatch_options = self.machine_type_configuration.get(
            "SubmitOptions", AttributeDict()
        )

        walltime = self.machine_type_configuration.Walltime
        mem = self.machine_meta_data.Memory
        node_type = self.machine_type_configuration.NodeType

        drone_environment = drone_environment_to_str(
            self.drone_environment(drone_uuid, machine_meta_data_translation_mapping),
            seperator=",",
            prefix="TardisDrone",
            customize_value=lambda x: convert_to(x, int, x),
        )

        return submit_cmd_option_formatter(
            AttributeDict(
                short=AttributeDict(
                    **sbatch_options.get("short", AttributeDict()),
                    j="oe",
                    m="p",
                    l=f"walltime={walltime},mem={mem}gb,nodes={node_type}",
                    v=f"{drone_environment}",
                ),
                long=AttributeDict(
                    **sbatch_options.get("long", AttributeDict()),
                ),
            )
        )

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TimeoutError as te:
            raise TardisTimeout from te
        except asyncssh.Error as exc:
            logger.warning("SSH connection failed: " + str(exc))
            raise TardisResourceStatusUpdateFailed from exc
        except IndexError as ide:
            raise TardisResourceStatusUpdateFailed from ide
        except TardisResourceStatusUpdateFailed:
            raise
        except CommandExecutionFailure as cef:
            raise TardisResourceStatusUpdateFailed from cef
        except Exception as ex:
            raise TardisError from ex
