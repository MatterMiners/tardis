from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin

import aiotelegraf


class TelegrafMonitoring(Plugin):
    def __init__(self):
        config = Configuration()

        self.host = config.Plugins.TelegrafMonitoring.host
        self.port = config.Plugins.TelegrafMonitoring.port
        self.default_tags = getattr(config.Plugins.TelegrafMonitoring, 'default_tags', None)

        self.client = aiotelegraf.Client(host=config.Plugins.TelegrafMonitoring.host,
                                         port=config.Plugins.TelegrafMonitoring.port,
                                         tags=getattr(config.Plugins.TelegrafMonitoring, 'default_tags', None))

    async def notify(self, state, resource_attributes):
        await self.client.connect()
        data = {'state': str(state)}
        data.update(resource_attributes)
        self.client.metric('tardis_metric', data)
        await self.client.close()
