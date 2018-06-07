from ..interfaces.siteadapter import SiteAdapter

import logging


class SiteAgent(SiteAdapter):
    def __init__(self, site_adapter):
        self._site_adapter = site_adapter

    async def deploy_resource(self, drone, *args, **kwargs):
        response = await self._site_adapter.deploy_resource(*args, **kwargs)
        return response

    @property
    def site_name(self):
        return self._site_adapter.site_name

    async def resource_status(self, drone, *args, **kwargs):
        return await self._site_adapter.resource_status(*args, **kwargs)

    async def terminate_resource(self, drone, *args, **kwargs):
        return await self._site_adapter.terminate_resource(*args, **kwargs)
