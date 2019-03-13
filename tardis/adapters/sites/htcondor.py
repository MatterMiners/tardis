from ...configuration.configuration import Configuration
from ...exceptions.tardisexceptions import TardisError
from ...interfaces.siteadapter import SiteAdapter
from ...utilities.asynccachemap import AsyncCacheMap
from ...utilities.attributedict import AttributeDict
from ...utilities.staticmapping import StaticMapping
from ...utilities.executors.shellexecutor import ShellExecutor

from contextlib import contextmanager
from datetime import datetime
from functools import partial

import re


async def htcondor_queue_updater(executor):
    attributes = dict(Owner="Owner", JobStatus="JobStatus", ClusterId="ClusterId", ProcId="ProcId")
    attributes_string = " ".join(attributes.values())
    queue_command = f"condor_q -af:t {attributes_string}"

    htcondor_queue = {}

    executor.run_command(queue_command)

    return htcondor_queue


class HTCondorSiteAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name):
        self.configuration = getattr(Configuration(), site_name)
        self._machine_type = machine_type
        self._site_name = site_name
        self._executor = getattr(self.configuration, 'executor', ShellExecutor())

        key_translator = StaticMapping(resource_id='cluster_id', created='created', updated='updated')
        translator_functions = StaticMapping(cluster_id=lambda x: int(x))

        self.handle_response = partial(self.handle_response, key_translator=key_translator,
                                       translator_functions=translator_functions)

        self._htcondor_queue = AsyncCacheMap(update_coroutine=partial(htcondor_queue_updater, self._executor),
                                             max_age=self.configuration.max_age * 60)

    async def deploy_resource(self, resource_attributes):
        submit_command = f"condor_submit {self.configuration.jdl}"
        response = await self._executor.run_command(submit_command)
        pattern = re.compile(r"^.*?(?P<jobs>\d+).*?(?P<cluster_id>\d+).$", flags=re.MULTILINE)
        response = AttributeDict(pattern.search(response.stdout).groupdict())
        now = datetime.now()
        response.update(AttributeDict(created=now, updated=now))
        return self.handle_response(response)

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
        await self._htcondor_queue.update_status()
        try:
            self._htcondor_queue[resource_attributes.resource_id]
        except KeyError:
            pass

    async def stop_resource(self, resource_attributes):
        """"Stopping machines is not supported in HTCondor, therefore terminate is called!"""
        return await self.terminate_resource(resource_attributes)

    async def terminate_resource(self, resource_attributes):
        terminate_command = f"condor_rm {resource_attributes.resource_id}"
        response = self._executor.run_command(terminate_command)
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except Exception as ex:
            raise TardisError from ex
