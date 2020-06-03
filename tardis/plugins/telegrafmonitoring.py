from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin
from ..interfaces.state import State
from ..utilities.attributedict import AttributeDict

import aiotelegraf
from datetime import datetime
import logging
import platform

logger = logging.getLogger("cobald.runtime.tardis.plugins.telegrafmonitoring")


class TelegrafMonitoring(Plugin):
    """
    The :py:class:`~tardis.plugins.telegrafmonitoring.TelegrafMonitoring`
    implements an interface to monitor state changes of the Drones in a telegraf
    service running a UDP input module.
    """

    def __init__(self):
        config = Configuration().Plugins.TelegrafMonitoring

        host = config.host
        port = config.port
        default_tags = dict(tardis_machine_name=platform.node())
        default_tags.update(getattr(config, "default_tags", {}))
        self.metric = getattr(config, "metric", "tardis_data")

        self.client = aiotelegraf.Client(host=host, port=port, tags=default_tags)

    async def notify(self, state: State, resource_attributes: AttributeDict) -> None:
        """
        Push changed state and updated meta-data of the drone into the telegraf server

        :param state: New state of the Drone
        :type state: State
        :param resource_attributes: Contains all meta-data of the Drone (created and
            updated timestamps, dns name, unique id, site_name, machine_type, etc.)
        :type resource_attributes: AttributeDict
        :return: None
        """
        logger.debug(f"Drone: {str(resource_attributes)} has changed state to {state}")
        await self.client.connect()
        data = dict(
            state=str(state),
            created=datetime.timestamp(resource_attributes.created),
            updated=datetime.timestamp(resource_attributes.updated),
        )
        tags = dict(
            site_name=resource_attributes.site_name,
            machine_type=resource_attributes.machine_type,
        )
        self.client.metric(self.metric, data, tags=tags)
        await self.client.close()
