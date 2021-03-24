from ...exceptions.executorexceptions import CommandExecutionFailure
from ...exceptions.tardisexceptions import TardisError
from ...exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ...interfaces.siteadapter import SiteAdapter
from ...interfaces.siteadapter import ResourceStatus
from ...utilities.asynccachemap import AsyncCacheMap
from ...utilities.attributedict import AttributeDict
from ...utilities.staticmapping import StaticMapping
from ...utilities.executors.shellexecutor import ShellExecutor
from ...utilities.utils import csv_parser, machine_meta_data_translation

from contextlib import contextmanager
from datetime import datetime
from functools import partial
from string import Template

import logging
import re

logger = logging.getLogger("cobald.runtime.tardis.adapters.sites.htcondor")


async def htcondor_queue_updater(executor):
    attributes = dict(
        Owner="Owner", JobStatus="JobStatus", ClusterId="ClusterId", ProcId="ProcId"
    )
    attributes_string = " ".join(attributes.values())
    queue_command = f"condor_q -af:t {attributes_string}"

    htcondor_queue = {}
    try:
        condor_queue = await executor.run_command(queue_command)
    except CommandExecutionFailure as cf:
        logger.warning(f"htcondor_queue_update failed: {cf}")
        raise
    else:
        for row in csv_parser(
            input_csv=condor_queue.stdout,
            fieldnames=tuple(attributes.keys()),
            delimiter="\t",
            replacements=dict(undefined=None),
        ):
            htcondor_queue[row["ClusterId"]] = row
        return htcondor_queue


# According to https://htcondor.readthedocs.io/en/latest/classad-attributes/
# job-classad-attributes.html
htcondor_status_codes = {
    "1": ResourceStatus.Booting,
    "2": ResourceStatus.Running,
    "3": ResourceStatus.Running,
    "4": ResourceStatus.Deleted,
    "5": ResourceStatus.Error,
    "6": ResourceStatus.Running,
    "7": ResourceStatus.Stopped,
}


class HTCondorAdapter(SiteAdapter):
    htcondor_machine_meta_data_translation_mapping = AttributeDict(
        Cores=1, Memory=1024, Disk=1024 * 1024
    )

    def __init__(self, machine_type: str, site_name: str):
        self._machine_type = machine_type
        self._site_name = site_name
        self._executor = getattr(self.configuration, "executor", ShellExecutor())

        key_translator = StaticMapping(
            remote_resource_uuid="ClusterId",
            resource_status="JobStatus",
            created="created",
            updated="updated",
        )

        # HTCondor uses digits to indicate job states and digit as variable names
        # are not allowed in Python, therefore the trick using an expanded
        # htcondor_status_code dictionary is necessary. Somehow ugly.
        translator_functions = StaticMapping(
            JobStatus=lambda x, translator=StaticMapping(
                **htcondor_status_codes
            ): translator[x]
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=translator_functions,
        )

        self._htcondor_queue = AsyncCacheMap(
            update_coroutine=partial(htcondor_queue_updater, self._executor),
            max_age=self.configuration.max_age * 60,
        )

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        jdl_file = self.machine_type_configuration.jdl
        with open(jdl_file, "r") as f:
            jdl_template = Template(f.read())

        drone_environment = self.drone_environment(
            resource_attributes.drone_uuid,
            resource_attributes.obs_machine_meta_data_translation_mapping,
        )

        submit_jdl = jdl_template.substitute(
            machine_meta_data_translation(
                self.machine_meta_data,
                self.htcondor_machine_meta_data_translation_mapping,
            ),
            Environment=";".join(
                f"TardisDrone{key}={value}" for key, value in drone_environment.items()
            ),
        )

        response = await self._executor.run_command(
            "condor_submit", stdin_input=submit_jdl
        )
        pattern = re.compile(
            r"^.*?(?P<Jobs>\d+).*?(?P<ClusterId>\d+).$", flags=re.MULTILINE
        )
        response = AttributeDict(pattern.search(response.stdout).groupdict())
        response.update(self.create_timestamps())
        return self.handle_response(response)

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        await self._htcondor_queue.update_status()
        try:
            resource_uuid = resource_attributes.remote_resource_uuid
            resource_status = self._htcondor_queue[resource_uuid]
        except KeyError:
            # In case the created timestamp is after last update timestamp of the
            # asynccachemap, no decision about the current state can be given,
            # since map is updated asynchronously.
            if (
                self._htcondor_queue.last_update - resource_attributes.created
            ).total_seconds() < 0:
                raise TardisResourceStatusUpdateFailed
            else:
                return AttributeDict(resource_status=ResourceStatus.Deleted)
        else:
            return self.handle_response(resource_status)

    async def _apply_condor_command(
        self, resource_attributes: AttributeDict, condor_command: str
    ):
        command = f"{condor_command} {resource_attributes.remote_resource_uuid}"
        try:
            response = await self._executor.run_command(command)
        except CommandExecutionFailure as cef:
            if cef.exit_code == 1 and "Couldn't find" in cef.stderr:
                # Happens if condor_suspend/condor_rm is called in the moment
                # the drone is shutting down itself. Repeat the procedure until
                # resource has vanished from condor_q call
                raise TardisResourceStatusUpdateFailed from cef
            raise
        pattern = re.compile(r"^.*?(?P<ClusterId>\d+).*$", flags=re.MULTILINE)
        response = AttributeDict(pattern.search(response.stdout).groupdict())
        return self.handle_response(response)

    async def stop_resource(self, resource_attributes: AttributeDict):
        """
        Stopping machines is equivalent to suspending jobs in HTCondor,
        therefore condor_suspend is called!
        """
        return await self._apply_condor_command(
            resource_attributes, condor_command="condor_suspend"
        )

    async def terminate_resource(self, resource_attributes: AttributeDict):
        return await self._apply_condor_command(
            resource_attributes, condor_command="condor_rm"
        )

    @staticmethod
    def create_timestamps():
        now = datetime.now()
        return AttributeDict(created=now, updated=now)

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TardisResourceStatusUpdateFailed:
            raise
        except Exception as ex:
            raise TardisError from ex
