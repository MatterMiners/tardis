from ..interfaces.siteadapter import SiteAdapter
from ..utilities.attributedict import convert_to_attribute_dict


class SiteAgent(SiteAdapter):
    def __init__(self, site_adapter):
        self._site_adapter = site_adapter

    async def deploy_resource(self, unique_id):
        with self._site_adapter.handle_exceptions():
            response = await self._site_adapter.deploy_resource(unique_id=unique_id)
            return convert_to_attribute_dict(response)

    def dns_name(self, unique_id):
        return self._site_adapter.dns_name(unique_id=unique_id)

    def handle_response(self, response):
        return NotImplemented

    @property
    def machine_type(self):
        return self._site_adapter.machine_type

    async def resource_status(self, resource_attributes):
        with self._site_adapter.handle_exceptions():
            return await self._site_adapter.resource_status(resource_attributes)

    @property
    def site_name(self):
        return self._site_adapter.site_name

    async def terminate_resource(self, resource_attributes):
        with self._site_adapter.handle_exceptions():
            return await self._site_adapter.terminate_resource(resource_attributes)
