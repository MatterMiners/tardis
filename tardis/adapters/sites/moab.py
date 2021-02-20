from ...exceptions.executorexceptions import CommandExecutionFailure
from ...exceptions.tardisexceptions import TardisError
from ...exceptions.tardisexceptions import TardisTimeout
from ...exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ...interfaces.siteadapter import ResourceStatus
from ...interfaces.siteadapter import SiteAdapter
from ...utilities.staticmapping import StaticMapping
from ...utilities.attributedict import AttributeDict
from ...utilities.attributedict import convert_to_attribute_dict
from ...utilities.executors.shellexecutor import ShellExecutor
from ...utilities.asynccachemap import AsyncCacheMap
from ...utilities.utils import submit_cmd_option_formatter

from asyncio import TimeoutError
from contextlib import contextmanager
from functools import partial
from datetime import datetime

import asyncssh
import logging
import re
import warnings
from xml.dom import minidom

logger = logging.getLogger("cobald.runtime.tardis.adapters.sites.moab")


async def moab_status_updater(executor):
    cmd = "showq --xml -w user=$(whoami) && showq -c --xml -w user=$(whoami)"
    logger.debug("Moab status update is running.")
    response = await executor.run_command(cmd)
    # combine two XML outputs to one
    xml_output = minidom.parseString(
        response["stdout"].replace("\n", "").replace("</Data><Data>", "")
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
    return moab_resource_status


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
            )
            self._startup_command = self.configuration.StartupCommand

        self._executor = getattr(self.configuration, "executor", ShellExecutor())

        self._moab_status = AsyncCacheMap(
            update_coroutine=partial(moab_status_updater, self._executor),
            max_age=self.configuration.StatusUpdate * 60,
        )
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

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        request_command = f"msub {self.msub_cmdline_options()} {self._startup_command}"
        result = await self._executor.run_command(request_command)
        logger.debug(f"{self.site_name} servers create returned {result}")

        remote_resource_uuid = int(result.stdout)
        resource_attributes.update(
            remote_resource_uuid=remote_resource_uuid,
            created=datetime.now(),
            updated=datetime.now(),
            drone_uuid=self.drone_uuid(remote_resource_uuid),
            resource_status=ResourceStatus.Booting,
        )
        return resource_attributes

    @staticmethod
    def check_remote_resource_uuid(resource_attributes, regex, response):
        pattern = re.compile(regex, flags=re.MULTILINE)
        remote_resource_uuid = int(pattern.findall(response)[0])
        if remote_resource_uuid != int(resource_attributes.remote_resource_uuid):
            raise TardisError(
                f"Failed to terminate {resource_attributes.remote_resource_uuid}."
            )
        else:
            resource_attributes.update(
                resource_status=ResourceStatus.Stopped, updated=datetime.now()
            )
        return remote_resource_uuid

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        await self._moab_status.update_status()
        # In case the created timestamp is after last update timestamp of the
        # asynccachemap, no decision about the current state can be given,
        # since map is updated asynchronously.
        try:
            resource_uuid = resource_attributes.remote_resource_uuid
            resource_status = self._moab_status[str(resource_uuid)]
        except KeyError:
            if (
                self._moab_status._last_update - resource_attributes.created
            ).total_seconds() < 0:
                raise TardisResourceStatusUpdateFailed
            else:
                resource_status = {
                    "JobID": resource_attributes.remote_resource_uuid,
                    "State": "Completed",
                }
        logger.debug(f"{self.site_name} has status {resource_status}.")
        resource_attributes.update(updated=datetime.now())
        return convert_to_attribute_dict(
            {**resource_attributes, **self.handle_response(resource_status)}
        )

    async def terminate_resource(self, resource_attributes: AttributeDict):
        request_command = f"canceljob {resource_attributes.remote_resource_uuid}"
        try:
            response = await self._executor.run_command(request_command)
        except CommandExecutionFailure as cf:
            if cf.exit_code == 1:
                logger.warning(
                    f"{self.site_name} servers terminate returned {cf.stdout}"
                )
                remote_resource_uuid = self.check_remote_resource_uuid(
                    resource_attributes,
                    r"ERROR:  invalid job specified \((\d*)\)",
                    cf.stderr,
                )
            else:
                raise cf
        else:
            logger.debug(f"{self.site_name} servers terminate returned {response}")
            remote_resource_uuid = self.check_remote_resource_uuid(
                resource_attributes, r"^job \'(\d*)\' cancelled", response.stdout
            )

        return self.handle_response(
            {"SystemJID": remote_resource_uuid}, **resource_attributes
        )

    async def stop_resource(self, resource_attributes: AttributeDict):
        logger.debug("MOAB jobs cannot be stopped gracefully. Terminating instead.")
        return await self.terminate_resource(resource_attributes)

    def msub_cmdline_options(self):
        sbatch_options = self.machine_type_configuration.get(
            "SubmitOptions", AttributeDict()
        )

        walltime = self.machine_type_configuration.Walltime
        mem = self.machine_meta_data.Memory
        node_type = self.machine_type_configuration.NodeType

        return submit_cmd_option_formatter(
            AttributeDict(
                short=AttributeDict(
                    **sbatch_options.get("short", AttributeDict()),
                    j="oe",
                    m="p",
                    l=f"walltime={walltime},mem={mem}gb,nodes={node_type}",
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
            raise TardisResourceStatusUpdateFailed
        except IndexError as ide:
            raise TardisResourceStatusUpdateFailed from ide
        except TardisResourceStatusUpdateFailed:
            raise
        except CommandExecutionFailure as cef:
            raise TardisResourceStatusUpdateFailed from cef
        except Exception as ex:
            raise TardisError from ex
