from abc import ABCMeta, abstractmethod


class SiteAdapter(metaclass=ABCMeta):
    @abstractmethod
    async def deploy_resource(self, *args, **kwargs):
        return NotImplemented

    @property
    def site_name(self):
        return NotImplemented

    @abstractmethod
    async def resource_status(self, *args, **kwargs):
        return NotImplemented

    @abstractmethod
    async def terminate_resource(self, *args, **kwargs):
        return NotImplemented
