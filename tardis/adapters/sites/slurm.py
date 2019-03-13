from ...configuration.configuration import Configuration
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...exceptions.tardisexceptions import TardisError
from ...exceptions.tardisexceptions import TardisTimeout
from ...exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ...interfaces.siteadapter import ResourceStatus
from ...interfaces.siteadapter import SiteAdapter
from ...utilities.staticmapping import StaticMapping
from ...utilities.attributedict import convert_to_attribute_dict
from ...utilities.executors.shellexecutor import ShellExecutor
from tardis.utilities.asynccachemap import AsyncCacheMap

from asyncio import TimeoutError
from contextlib import contextmanager
from functools import partial
from datetime import datetime
from io import StringIO
import csv

import logging
import re


async def slurm_status_updater(executor):
    attributes = dict(JobId='JOBID', Host='NodeList', State='State')
    # Escape slurm expressions and add them to attributes
    attributes.update({key: value for key, value in Configuration().BatchSystem.ratios.items()})
    cmd = f'sacct -o "JobID,NodeList,State" -n -P'
    slurm_resource_status = {}
    logging.debug("Slurm status update is running.")
    slurm_status = await executor.run_command(cmd)
    with StringIO(slurm_status.stdout) as csv_input:
        cvs_reader = csv.DictReader(csv_input, fieldnames=tuple(attributes.keys()), delimiter='|')
        for row in cvs_reader:
            slurm_resource_status[row['JobId']] = row
    logging.debug("Slurm status update finished.")
    return slurm_resource_status


class SlurmAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name):
        self.configuration = getattr(Configuration(), site_name)
        self._machine_type = machine_type
        self._site_name = site_name
        self._startup_command = self.configuration.StartupCommand

        self._executor = getattr(self.configuration, 'executor', ShellExecutor())

        self._slurm_status = AsyncCacheMap(update_coroutine=partial(slurm_status_updater, self._executor),
                                           max_age=self.configuration.StatusUpdate * 60)

        key_translator = StaticMapping(resource_id='JobId', resource_status='State')

        # see job state codes at https://slurm.schedmd.com/squeue.html
        translator_functions = StaticMapping(State=lambda x, translator=StaticMapping(BOOT_FAIL=ResourceStatus.Error,
                                                                                      CANCELLED=ResourceStatus.Error,
                                                                                      COMPLETED=ResourceStatus.Stopped,
                                                                                      DEADLINE=ResourceStatus.Stopped,
                                                                                      FAILED=ResourceStatus.Error,
                                                                                      NODE_FAIL=ResourceStatus.Error,
                                                                                      OUT_OF_MEMORY=
                                                                                      ResourceStatus.Error,
                                                                                      PENDING=ResourceStatus.Booting,
                                                                                      RUNNING=ResourceStatus.Running,
                                                                                      REQUEUED=ResourceStatus.Error,
                                                                                      RESIZING=ResourceStatus.Error,
                                                                                      REVOKED=ResourceStatus.Error,
                                                                                      SUSPENDED=ResourceStatus.Running,
                                                                                      TIMEOUT=ResourceStatus.Stopped):
                                             translator[x],
                                             JobId=lambda x: int(x))

        self.handle_response = partial(self.handle_response, key_translator=key_translator,
                                       translator_functions=translator_functions)

    async def deploy_resource(self, resource_attributes):
        request_command = f'sbatch -p {self.configuration.MachineTypeConfiguration[self._machine_type].Partition} ' \
                          f'-N 1 -n {self.machine_meta_data.Cores} ' \
                          f'--mem={self.machine_meta_data.Memory}gb ' \
                          f'-t {self.configuration.MachineTypeConfiguration[self._machine_type].Walltime} ' \
                          f'{self._startup_command}'
        result = await self._executor.run_command(request_command)
        logging.debug(f"{self.site_name} servers create returned {result}")
        pattern = re.compile(r'^Submitted batch job (\d*)', flags=re.MULTILINE)
        resource_id = int(pattern.findall(result.stdout)[0])
        resource_attributes.update(resource_id=resource_id, created=datetime.now(), updated=datetime.now(),
                                   dns_name=self.dns_name(resource_id), resource_status=ResourceStatus.Booting)
        return resource_attributes

    @property
    def machine_meta_data(self):
        return self.configuration.MachineMetaData[self._machine_type]

    @property
    def machine_type(self):
        return self._machine_type

    @property
    def site_name(self):
        return self._site_name

    async def resource_status(self, resource_attributes):
        await self._slurm_status.update_status()
        resource_status = self._slurm_status[str(resource_attributes.resource_id)]
        logging.debug(f'{self.site_name} has status {resource_status}.')
        resource_attributes.update(updated=datetime.now())
        if self.configuration.UpdateDnsName and resource_status['Host'] != 'None assigned':
            resource_attributes.update(dns_name=resource_status['Host'])
        return convert_to_attribute_dict({**resource_attributes, **self.handle_response(resource_status)})

    async def terminate_resource(self, resource_attributes):
        request_command = f"scancel {resource_attributes.resource_id}"
        await self._executor.run_command(request_command)
        resource_attributes.update(resource_status=ResourceStatus.Stopped, updated=datetime.now())
        return self.handle_response({'JobId': resource_attributes.resource_id}, **resource_attributes)

    async def stop_resource(self, resource_attributes):
        logging.debug('Slurm jobs cannot be stopped gracefully. Terminating instead.')
        return await self.terminate_resource(resource_attributes)

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except CommandExecutionFailure as ex:
            logging.info("Execute command failed: %s" % str(ex))
            raise TardisResourceStatusUpdateFailed
        except TimeoutError as te:
            raise TardisTimeout from te
        except Exception as ex:
            raise TardisError from ex
