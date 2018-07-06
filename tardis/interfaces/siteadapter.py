from abc import ABCMeta, abstractmethod


class SiteAdapter(metaclass=ABCMeta):
    @abstractmethod
    async def deploy_resource(self, unique_id):
        return NotImplemented

    def dns_name(self, unique_id):
        return "{}-{}".format(self.site_name.lower(), unique_id, self.machine_type.lower())

    @abstractmethod
    def handle_response(self, response):
        return NotImplemented

    @property
    def machine_type(self):
        return NotImplemented

    @abstractmethod
    async def resource_status(self, resource_attributes):
        return NotImplemented

    @property
    def site_name(self):
        return NotImplemented

    @abstractmethod
    async def terminate_resource(self, resource_attributes):
        return NotImplemented
