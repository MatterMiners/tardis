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
    csv_parser,
    submit_cmd_option_formatter,
)

from asyncio import TimeoutError
from contextlib import contextmanager
from functools import partial
from typing import Iterable, Mapping, Tuple

import logging
import re
import warnings

logger = logging.getLogger("cobald.runtime.tardis.adapters.sites.slurm")


async def squeue(
    *resource_attributes: Tuple[AttributeDict, ...], executor: Executor
) -> Iterable[Mapping]:
    attributes = dict(JobId="%A", Host="%N", State="%T")
    attributes_string = "|".join(attributes.values())

    remote_resource_ids = ",".join(
        str(resource.remote_resource_uuid) for resource in resource_attributes
    )

    cmd = f'squeue -o "{attributes_string}" -h -t all --job={remote_resource_ids}'

    slurm_resource_status = {}
    logger.debug("Slurm status update is started.")
    try:
        slurm_status = await executor.run_command(cmd)
    except CommandExecutionFailure as cf:
        logger.warning(f"Slurm status update has failed due to {cf}.")
        raise
    else:
        for row in csv_parser(
            slurm_status.stdout, fieldnames=tuple(attributes.keys()), delimiter="|"
        ):
            row["State"] = row["State"].strip()
            slurm_resource_status[row["JobId"]] = row
        logger.debug("Slurm status update finished.")

        return (
            slurm_resource_status.get(
                str(resource.remote_resource_uuid),
                # assume that jobs that do not show up (anymore) in squeue have
                # State COMPLETED (Deleted)
                {
                    "State": "COMPLETED",
                },
            )
            for resource in resource_attributes
        )


class SlurmAdapter(SiteAdapter):
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
            remote_resource_uuid="JobId", resource_status="State"
        )

        # see job state codes at https://slurm.schedmd.com/squeue.html#lbAG
        translator_functions = StaticMapping(
            State=lambda x, translator=StaticMapping(
                CANCELLED=ResourceStatus.Deleted,
                COMPLETED=ResourceStatus.Deleted,
                COMPLETING=ResourceStatus.Running,
                CONFIGURING=ResourceStatus.Booting,
                PENDING=ResourceStatus.Booting,
                PREEMPTED=ResourceStatus.Deleted,
                RESV_DEL_HOLD=ResourceStatus.Stopped,
                REQUEUE_FED=ResourceStatus.Booting,
                REQUEUE_HOLD=ResourceStatus.Booting,
                REQUEUED=ResourceStatus.Booting,
                RESIZING=ResourceStatus.Running,
                RUNNING=ResourceStatus.Running,
                SIGNALING=ResourceStatus.Running,
                SPECIAL_EXIT=ResourceStatus.Booting,
                STAGE_OUT=ResourceStatus.Running,
                STOPPED=ResourceStatus.Stopped,
                SUSPENDED=ResourceStatus.Stopped,
                TIMEOUT=ResourceStatus.Deleted,
            ): translator.get(x, default=ResourceStatus.Error),
            JobId=lambda x: int(x),
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=translator_functions,
        )

        bulk_size = getattr(self.configuration, "bulk_size", 100)
        bulk_delay = getattr(self.configuration, "bulk_delay", 1.0)

        self._squeue = AsyncBulkCall(
            partial(squeue, executor=self._executor),
            size=bulk_size,
            delay=bulk_delay,
        )

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        sbatch_cmdline_option_string = submit_cmd_option_formatter(
            self.sbatch_cmdline_options(
                resource_attributes.drone_uuid,
                resource_attributes.obs_machine_meta_data_translation_mapping,
            )
        )

        request_command = (
            f"sbatch {sbatch_cmdline_option_string} {self._startup_command}"
        )

        result = await self._executor.run_command(request_command)
        logger.debug(f"{self.site_name} sbatch returned {result}")
        pattern = re.compile(r"^Submitted batch job (\d*)", flags=re.MULTILINE)
        remote_resource_uuid = int(pattern.findall(result.stdout)[0])

        return AttributeDict(
            remote_resource_uuid=remote_resource_uuid,
            resource_status=ResourceStatus.Booting,
        )

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        return self.handle_response(await self._squeue(resource_attributes))

    async def terminate_resource(self, resource_attributes: AttributeDict) -> None:
        request_command = f"scancel {resource_attributes.remote_resource_uuid}"
        await self._executor.run_command(request_command)

    def sbatch_cmdline_options(self, drone_uuid, machine_meta_data_translation_mapping):
        sbatch_options = self.machine_type_configuration.get(
            "SubmitOptions", AttributeDict()
        )

        walltime = self.machine_type_configuration.Walltime

        drone_environment = drone_environment_to_str(
            self.drone_environment(drone_uuid, machine_meta_data_translation_mapping),
            seperator=",",
            prefix="TardisDrone",
            customize_value=lambda x: convert_to(x, int, x),
        )

        return AttributeDict(
            short=AttributeDict(
                **sbatch_options.get("short", AttributeDict()),
                p=self.machine_type_configuration.Partition,
                N=1,
                n=self.machine_meta_data.Cores,
                t=self.machine_type_configuration.Walltime,
            ),
            long=AttributeDict(
                **sbatch_options.get("long", AttributeDict()),
                # slurm does not accept floating point variables for memory,
                # therefore use internally megabytes and convert it to an integer
                # to allow for request i.e. 2.5 GB in the machine meta data. According
                # to http://cern.ch/go/x7p8 SLURM is using factors of 1024 to convert
                # between memory units
                mem=f"{int(self.machine_meta_data.Memory * 1024)}mb",
                export=f"SLURM_Walltime={walltime},{drone_environment}",
            ),
        )

    async def stop_resource(self, resource_attributes: AttributeDict) -> None:
        logger.debug("Slurm jobs cannot be stopped gracefully. Terminating instead.")
        await self.terminate_resource(resource_attributes)

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except CommandExecutionFailure as ex:
            logger.warning("Execute command failed: %s" % str(ex))
            raise TardisResourceStatusUpdateFailed from ex
        except TardisResourceStatusUpdateFailed:
            raise
        except TimeoutError as te:
            raise TardisTimeout from te
        except Exception as ex:
            raise TardisError from ex
