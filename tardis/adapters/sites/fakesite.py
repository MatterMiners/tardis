from ...configuration.configuration import Configuration
from ...exceptions.tardisexceptions import TardisError
from ...interfaces.siteadapter import SiteAdapter

from contextlib import contextmanager


class FakeSiteAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name):
        self.configuration = getattr(Configuration(), site_name)
        self._machine_type = machine_type
        self._site_name = site_name

    async def deploy_resource(self, resource_attributes):
        ...

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
        ...

    async def stop_resource(self, resource_attributes):
        ...

    async def terminate_resource(self, resource_attributes):
        ...

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except Exception as ex:
            raise TardisError from ex
