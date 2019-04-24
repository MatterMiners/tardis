from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin

import aiotelegraf


class TelegrafMonitoring(Plugin):
    def __init__(self):
        config = Configuration()

        host = config.Plugins.TelegrafMonitoring.host
        port = config.Plugins.TelegrafMonitoring.port
        default_tags = getattr(config.Plugins.TelegrafMonitoring, 'default_tags', None)

        self.client = aiotelegraf.Client(host=host, port=port, tags=default_tags)

    async def notify(self, state, resource_attributes):
        await self.client.connect()
        data = dict(state=str(state), created=resource_attributes.created,
                    updated=resource_attributes.updated)
        tags = dict(site_name=resource_attributes.site_name,
                    machine_type=resource_attributes.machine_type)
        self.client.metric('tardis_data', data, tags=tags)
        await self.client.close()
