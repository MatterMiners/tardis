from ...configuration.configuration import Configuration
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

from asyncio import TimeoutError
from contextlib import contextmanager
from functools import partial
from datetime import datetime

import asyncssh
import logging
import re
import warnings
from xml.dom import minidom


async def moab_status_updater(executor):
    cmd = "showq --xml -w user=$(whoami) && showq -c --xml -w user=$(whoami)"
    logging.debug("Moab status update is running.")
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
    logging.debug("Moab status update completed")
    return moab_resource_status


class MoabAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str):
        self._configuration = getattr(Configuration(), site_name)
        self._machine_type = machine_type
        self._site_name = site_name

        try:
            self._startup_command = self.machine_type_configuration.StartupCommand
        except AttributeError:
            warnings.warn(
                "StartupCommand has been moved to the machine_type_configuration!",
                DeprecationWarning,
            )
            self._startup_command = self._configuration.StartupCommand

        self._executor = getattr(self._configuration, "executor", ShellExecutor())

        self._moab_status = AsyncCacheMap(
            update_coroutine=partial(moab_status_updater, self._executor),
            max_age=self._configuration.StatusUpdate * 60,
        )
        key_translator = StaticMapping(
            remote_resource_uuid="JobID", resource_status="State"
        )

        translator_functions = StaticMapping(
            State=lambda x, translator=StaticMapping(
                Idle=ResourceStatus.Booting,
                Running=ResourceStatus.Running,
                Completed=ResourceStatus.Deleted,
                Canceling=ResourceStatus.Running,
                Vacated=ResourceStatus.Stopped,
            ): translator[x],
            JobID=lambda x: int(x),
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=translator_functions,
        )

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        request_command = (
            f"msub -j oe -m p -l "
            f"walltime={self.machine_type_configuration.Walltime},"
            f"mem={self.machine_meta_data.Memory}gb,"
            f"nodes={self.machine_type_configuration.NodeType} "
            f"{self._startup_command}"
        )
        result = await self._executor.run_command(request_command)
        logging.debug(f"{self.site_name} servers create returned {result}")

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
        logging.debug(f"{self.site_name} has status {resource_status}.")
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
                logging.debug(
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
            logging.debug(f"{self.site_name} servers terminate returned {response}")
            remote_resource_uuid = self.check_remote_resource_uuid(
                resource_attributes, r"^job \'(\d*)\' cancelled", response.stdout
            )

        return self.handle_response(
            {"SystemJID": remote_resource_uuid}, **resource_attributes
        )

    async def stop_resource(self, resource_attributes: AttributeDict):
        logging.debug("MOAB jobs cannot be stopped gracefully. Terminating instead.")
        return await self.terminate_resource(resource_attributes)

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TimeoutError as te:
            raise TardisTimeout from te
        except asyncssh.Error as exc:
            logging.info("SSH connection failed: " + str(exc))
            raise TardisResourceStatusUpdateFailed
        except IndexError as ide:
            raise TardisResourceStatusUpdateFailed from ide
        except TardisResourceStatusUpdateFailed:
            raise
        except CommandExecutionFailure as cef:
            raise TardisResourceStatusUpdateFailed from cef
        except Exception as ex:
            raise TardisError from ex
