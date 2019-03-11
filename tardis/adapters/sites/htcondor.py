from ...configuration.configuration import Configuration
from ...exceptions.tardisexceptions import TardisError
from ...interfaces.siteadapter import SiteAdapter
from ...utilities.executors.shellexecutor import ShellExecutor

from contextlib import contextmanager


class HTCondorSiteAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name):
        self.configuration = getattr(Configuration(), site_name)
        self._machine_type = machine_type
        self._site_name = site_name
        self._executor = getattr(self.configuration, 'executor', ShellExecutor())

    async def deploy_resource(self, resource_attributes):
        pass

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
        pass

    async def stop_resource(self, resource_attributes):
        pass

    async def terminate_resource(self, resource_attributes):
        pass

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except Exception as ex:
            raise TardisError from ex
