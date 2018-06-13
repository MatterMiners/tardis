from ..interfaces.siteadapter import SiteAdapter


class SiteAgent(SiteAdapter):
    def __init__(self, site_adapter):
        self._site_adapter = site_adapter

    async def deploy_resource(self, unique_id, **kwargs):
        with self._site_adapter.handle_exceptions():
            response = await self._site_adapter.deploy_resource(unique_id=unique_id, **kwargs)
            return response

    def dns_name(self, unique_id):
        return self._site_adapter.dns_name(unique_id=unique_id)

    def handle_response(self, response):
        return NotImplemented

    @property
    def machine_type(self):
        return self._site_adapter.machine_type

    async def resource_status(self, drone, **kwargs):
        with self._site_adapter.handle_exceptions():
            return await self._site_adapter.resource_status(**kwargs)

    @property
    def site_name(self):
        return self._site_adapter.site_name

    async def terminate_resource(self, drone, **kwargs):
        with self._site_adapter.handle_exceptions():
            return await self._site_adapter.terminate_resource(**kwargs)
