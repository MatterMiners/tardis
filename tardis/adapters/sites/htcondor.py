from ...configuration.configuration import Configuration
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...exceptions.tardisexceptions import TardisError
from ...exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ...interfaces.siteadapter import SiteAdapter
from ...interfaces.siteadapter import ResourceStatus
from ...utilities.asynccachemap import AsyncCacheMap
from ...utilities.attributedict import AttributeDict
from ...utilities.staticmapping import StaticMapping
from ...utilities.executors.shellexecutor import ShellExecutor
from ...utilities.utils import htcondor_csv_parser

from contextlib import contextmanager
from datetime import datetime
from functools import partial
from string import Template

import logging
import re


async def htcondor_queue_updater(executor):
    attributes = dict(Owner="Owner", JobStatus="JobStatus", ClusterId="ClusterId", ProcId="ProcId")
    attributes_string = " ".join(attributes.values())
    queue_command = f"condor_q -af:t {attributes_string}"

    htcondor_queue = {}
    try:
        condor_queue = await executor.run_command(queue_command)
    except CommandExecutionFailure as cf:
        logging.error(f"htcondor_queue_update failed: {cf}")
        raise
    else:
        for row in htcondor_csv_parser(htcondor_input=condor_queue.stdout, fieldnames=tuple(attributes.keys()),
                                       delimiter='\t', replacements=dict(undefined=None)):
            htcondor_queue[row['ClusterId']] = row
        return htcondor_queue


htcondor_status_codes = {'0': ResourceStatus.Error,
                         '1': ResourceStatus.Booting,
                         '2': ResourceStatus.Running,
                         '3': ResourceStatus.Stopped,
                         '4': ResourceStatus.Deleted,
                         '5': ResourceStatus.Error,
                         '6': ResourceStatus.Error}

htcondor_translate_resources_prefix = {'Cores': 1,
                                       'Memory': 1024,
                                       'Disk': 1024}


class HTCondorAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str):
        self.configuration = getattr(Configuration(), site_name)
        self._machine_type = machine_type
        self._site_name = site_name
        self._executor = getattr(self.configuration, 'executor', ShellExecutor())

        key_translator = StaticMapping(remote_resource_uuid='ClusterId', resource_status='JobStatus',
                                       created='created', updated='updated')

        # HTCondor uses digits to indicate job states and digit as variable names are not allowed in Python, therefore
        # the trick using an expanded htcondor_status_code dictionary is necessary. Somehow ugly.
        translator_functions = StaticMapping(JobStatus=lambda x, translator=StaticMapping(**htcondor_status_codes):
                                             translator[x])

        self.handle_response = partial(self.handle_response, key_translator=key_translator,
                                       translator_functions=translator_functions)

        self._htcondor_queue = AsyncCacheMap(update_coroutine=partial(htcondor_queue_updater, self._executor),
                                             max_age=self.configuration.max_age * 60)

    async def deploy_resource(self, resource_attributes: AttributeDict) -> AttributeDict:
        with open(self.configuration.MachineTypeConfiguration[self._machine_type].jdl, 'r') as f:
            jdl_template = Template(f.read())

        try:
            translated_meta_data = {key: htcondor_translate_resources_prefix[key] * value for key, value in
                                    self.machine_meta_data.items()}
        except KeyError as ke:
            logging.error(f"deploy_resource failed: no translation known for {ke}")
            raise
        else:
            translated_meta_data['Uuid'] = resource_attributes.drone_uuid

        submit_jdl = jdl_template.substitute(translated_meta_data,
                                             Environment=";".join(f"TardisDrone{key}={value}"
                                                                  for key, value in translated_meta_data.items()))

        response = await self._executor.run_command("condor_submit", stdin_input=submit_jdl)
        pattern = re.compile(r"^.*?(?P<Jobs>\d+).*?(?P<ClusterId>\d+).$", flags=re.MULTILINE)
        response = AttributeDict(pattern.search(response.stdout).groupdict())
        response.update(self.create_timestamps())
        return self.handle_response(response)

    @property
    def machine_meta_data(self) -> AttributeDict:
        return self.configuration.MachineMetaData[self._machine_type]

    @property
    def machine_type(self) -> str:
        return self._machine_type

    @property
    def site_name(self) -> str:
        return self._site_name

    async def resource_status(self, resource_attributes: AttributeDict) -> AttributeDict:
        await self._htcondor_queue.update_status()
        try:
            resource_status = self._htcondor_queue[resource_attributes.remote_resource_uuid]
        except KeyError:
            # In case the created timestamp is after last update timestamp of the asynccachemap,
            # no decision about the current state can be given, since map is updated asynchronously.
            if (self._htcondor_queue.last_update - resource_attributes.created).total_seconds() < 0:
                raise TardisResourceStatusUpdateFailed
            else:
                return AttributeDict(resource_status=ResourceStatus.Deleted)
        else:
            return self.handle_response(resource_status)

    async def stop_resource(self, resource_attributes: AttributeDict):
        """"Stopping machines is not supported in HTCondor, therefore terminate is called!"""
        return await self.terminate_resource(resource_attributes)

    async def terminate_resource(self, resource_attributes: AttributeDict):
        terminate_command = f"condor_rm {resource_attributes.remote_resource_uuid}"
        try:
            response = await self._executor.run_command(terminate_command)
        except CommandExecutionFailure as cef:
            if cef.exit_code == 1 and "Couldn't find/remove" in cef.stderr:
                # Happens if condor_rm is called in the moment the drone is shutting down itself
                # Repeat the procedure until resource has vanished from condor_status call
                raise TardisResourceStatusUpdateFailed from cef
            raise
        pattern = re.compile(r"^.*?(?P<ClusterId>\d+).*$", flags=re.MULTILINE)
        response = AttributeDict(pattern.search(response.stdout).groupdict())
        return self.handle_response(response)

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
