from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin

import aiotelegraf
from datetime import datetime
import logging


class TelegrafMonitoring(Plugin):
    def __init__(self):
        self.logger = logging.getLogger("telegrafmonitoring")
        self.logger.setLevel(logging.DEBUG)
        config = Configuration().Plugins.TelegrafMonitoring

        host = config.host
        port = config.port
        default_tags = getattr(config, 'default_tags', None)
        self.metric = getattr(config, 'metric', 'tardis_data')

        self.client = aiotelegraf.Client(host=host, port=port, tags=default_tags)

    async def notify(self, state, resource_attributes):
        self.logger.debug(f"Drone: {str(resource_attributes)} has changed state to {state}")
        await self.client.connect()
        data = dict(state=str(state), created=datetime.timestamp(resource_attributes.created),
                    updated=datetime.timestamp(resource_attributes.updated))
        tags = dict(site_name=resource_attributes.site_name,
                    machine_type=resource_attributes.machine_type)
        self.client.metric(self.metric, data, tags=tags)
        await self.client.close()
