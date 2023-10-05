from typing import Iterable, Tuple, Awaitable, Mapping
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...exceptions.tardisexceptions import TardisError
from ...exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ...interfaces.siteadapter import SiteAdapter
from ...interfaces.siteadapter import ResourceStatus
from ...interfaces.executor import Executor
from ...utilities.attributedict import AttributeDict
from ...utilities.staticmapping import StaticMapping
from ...utilities.executors.shellexecutor import ShellExecutor
from ...utilities.asyncbulkcall import AsyncBulkCall
from ...utilities.utils import (
    csv_parser,
    drone_environment_to_str,
    machine_meta_data_translation,
)

from contextlib import contextmanager
from functools import partial
from string import Template

import warnings
import logging
import re

logger = logging.getLogger("cobald.runtime.tardis.adapters.sites.htcondor")


# TODO: Remove this once the old-style UUIDs are deprecated
def _job_id(resource_uuid: str) -> str:
    """
    Normalize single "ClusterID" and bulk "ClusterID.ProcID" UUIDs to job IDs
    """
    return resource_uuid if "." in resource_uuid else f"{resource_uuid}.0"


async def condor_q(
    *resource_attributes: Tuple[AttributeDict, ...], executor: Executor
) -> Iterable[Mapping]:
    attributes = dict(JobStatus="JobStatus", ClusterId="ClusterId", ProcId="ProcId")
    attributes_string = " ".join(attributes.values())

    remote_resource_ids = " ".join(
        _job_id(resource.remote_resource_uuid) for resource in resource_attributes
    )

    queue_command = f"condor_q {remote_resource_ids} -af:t {attributes_string}"

    htcondor_queue = {}
    try:
        condor_queue = await executor.run_command(queue_command)
    except CommandExecutionFailure as cf:
        logger.warning(f"{queue_command} failed with: {cf}")
        raise
    else:
        for row in csv_parser(
            input_csv=condor_queue.stdout,
            fieldnames=tuple(attributes.keys()),
            delimiter="\t",
            replacements=dict(undefined=None),
        ):
            row["JobId"] = f"{row['ClusterId']}.{row['ProcId']}"
            htcondor_queue[row["JobId"]] = row

        return (
            htcondor_queue.get(
                _job_id(resource.remote_resource_uuid),
                # assume that jobs that do not show up (anymore) in condor_q have
                # JobStatus 4 (Deleted)
                {
                    "JobStatus": "4",
                },
            )
            for resource in resource_attributes
        )


JDL = str
# search the Job ID in a submit Proc line
SUBMIT_ID_PATTERN = re.compile(r"Proc\s(\d+\.\d+)")
# search for job queue commands
JDL_QUEUE_PATTERN = re.compile(r"^queue\s*\d*\s*$", flags=re.MULTILINE)


def _submit_description(resource_jdls: Tuple[JDL, ...]) -> str:
    commands = []
    for jdl in resource_jdls:
        commands.append(jdl)
        if JDL_QUEUE_PATTERN.search(jdl):
            warnings.warn(
                "Condor JDL templates may not include queue commands",
                FutureWarning,
                stacklevel=2,
            )
        else:
            commands.append("queue 1")
    return "\n".join(commands)


async def condor_submit(*resource_jdls: JDL, executor: Executor) -> Iterable[str]:
    """Submit a number of resources from their JDL, reporting the new Job ID for each"""
    # verbose submit gives an ordered listing of class ads, such as
    # ** Proc 15556.0:
    # Args = "150"
    # ClusterId = 15556
    # ...
    # ProcId = 0
    # QDate = 1641289701
    # ...
    #
    # ** Proc 15556.1:
    # ...
    command = f"condor_submit -verbose -maxjobs {len(resource_jdls)}"
    response = await executor.run_command(
        command,
        stdin_input=_submit_description(resource_jdls),
    )
    return (
        SUBMIT_ID_PATTERN.search(line).group(1)
        for line in response.stdout.splitlines()
        if line.startswith("** Proc")
    )


# condor_rm and condor_suspend are actually the same tool under the hood
# they only differ in the method called on the Schedd and their success message
def condor_rm(
    *resource_attributes: AttributeDict, executor: Executor
) -> Awaitable[Iterable[bool]]:
    """Remove a number of resources, indicating success for each"""
    return _condor_tool(
        resource_attributes, executor, "condor_rm", "marked for removal"
    )


def condor_suspend(
    *resource_attributes: AttributeDict, executor: Executor
) -> Awaitable[Iterable[bool]]:
    """Suspend a number of resources, indicating success for each"""
    return _condor_tool(resource_attributes, executor, "condor_suspend", "suspended")


# search the Job ID in a remove/suspend mark line
TOOL_ID_PATTERN = re.compile(r"Job\s(\d+\.\d+)")


async def _condor_tool(
    resource_attributes: Tuple[AttributeDict, ...],
    executor: Executor,
    command: str,
    success_message: str,
) -> Iterable[bool]:
    """
    Generic call to modify a number of condor jobs and indicate success for each

    The ``command`` and ``success_message`` should match the specific tool,
    e.g. ``condor_rm`` reports ``Job XY.Z marked for removal`` and thus corresponds to
    ``_condor_tool(..., "condor_rm", "marked for removal")``.
    """
    command = (
        command
        + " "
        + " ".join(
            _job_id(resource.remote_resource_uuid) for resource in resource_attributes
        )
    )
    try:
        response = await executor.run_command(command)
    except CommandExecutionFailure as cef:
        # the tool fails if none of the jobs are found – because they all just shut down
        # report graceful failure for all
        if cef.exit_code == 1 and "not found" in cef.stderr:
            return [False] * len(resource_attributes)
        raise
    # successes are in stdout, failures in stderr, both in argument order
    # stdout: Job 15540.0 marked for removal
    # stderr: Job 15612.0 not found
    # stderr: Job 15535.0 marked for removal
    success_jobs = {
        TOOL_ID_PATTERN.search(line).group(1)
        for line in response.stdout.splitlines()
        if line.endswith(success_message)
    }
    return (
        _job_id(resource.remote_resource_uuid) in success_jobs
        for resource in resource_attributes
    )


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

    def __init__(
        self,
        machine_type: str,
        site_name: str,
    ):
        self._machine_type = machine_type
        self._site_name = site_name
        self._executor = getattr(self.configuration, "executor", ShellExecutor())
        bulk_size = getattr(self.configuration, "bulk_size", 100)
        bulk_delay = getattr(self.configuration, "bulk_delay", 1.0)
        self._condor_submit, self._condor_suspend, self._condor_rm = (
            AsyncBulkCall(
                partial(tool, executor=self._executor),
                size=bulk_size,
                delay=bulk_delay,
            )
            for tool in (condor_submit, condor_suspend, condor_rm)
        )
        self._condor_q = AsyncBulkCall(
            partial(condor_q, executor=self._executor),
            size=bulk_size,
            delay=bulk_delay,
        )

        key_translator = StaticMapping(
            remote_resource_uuid="JobId",
            resource_status="JobStatus",
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
            Environment=drone_environment_to_str(
                drone_environment, seperator=";", prefix="TardisDrone"
            ),
            Arguments=drone_environment_to_str(
                drone_environment, seperator=" ", prefix="--", customize_key=str.lower
            ),
        )

        job_id = await self._condor_submit(submit_jdl)
        response = AttributeDict(JobId=job_id)

        return self.handle_response(response)

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        return self.handle_response(await self._condor_q(resource_attributes))

    async def stop_resource(self, resource_attributes: AttributeDict) -> None:
        """
        Stopping machines is equivalent to suspending jobs in HTCondor,
        therefore condor_suspend is called!
        """
        resource_uuid = resource_attributes.remote_resource_uuid
        if await self._condor_suspend(resource_attributes):
            return
        logger.debug(f"condor_suspend failed for {resource_uuid}")
        raise TardisResourceStatusUpdateFailed

    async def terminate_resource(self, resource_attributes: AttributeDict) -> None:
        resource_uuid = resource_attributes.remote_resource_uuid
        if await self._condor_rm(resource_attributes):
            return
        logger.debug(f"condor_rm failed for {resource_uuid}")
        raise TardisResourceStatusUpdateFailed

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TardisResourceStatusUpdateFailed:
            raise
        except Exception as ex:
            raise TardisError from ex
