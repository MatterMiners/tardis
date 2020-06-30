from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin
from ..interfaces.state import State
from ..utilities.attributedict import AttributeDict

import logging
import asyncio
from elasticsearch import Elasticsearch
from time import time
from datetime import datetime


class ElasticsearchMonitoring(Plugin):
    """
    The :py:class:`~tardis.plugins.elasticsearchmonitoring.ElasticsearchMonitoring`
    implements an interface to monitor the state of the Drones using Elasticsearch.
    """

    def __init__(self):
        self.logger = logging.getLogger(
            "cobald.runtime.tardis.plugins.elasticsearchmonitoring"
        )
        config = Configuration().Plugins.ElasticsearchMonitoring

        self._index = config.index
        self._meta = getattr(config, "meta", "")

        self._es = Elasticsearch([{"host": config.host, "port": config.port}])

    async def notify(self, state: State, resource_attributes: AttributeDict) -> None:
        """
        Pushes drone info at every state change to an ElasticSearch instance.

        :param state: New state of the Drone
        :type state: State
        :param resource_attributes: Contains all meta-data of the Drone (created and
            updated timestamps, dns name, unique id, site_name, machine_type, etc.)
        :type resource_attributes: AttributeDict
        :return: None
        """
        self.logger.debug(
            f"Drone: {str(resource_attributes)} has changed state to {state}"
        )

        document = {
            **resource_attributes,
            "state": str(state),
            "meta": self._meta,
            "timestamp": int(time() * 1000),
            "resource_status": str(resource_attributes["resource_status"]),
        }

        await self.async_execute(document)

    async def async_execute(self, document: AttributeDict) -> None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, document)

    def execute(self, document: AttributeDict) -> None:
        """
        Pushes drone info to an ElasticSearch instance.

        :param document: Contains all meta-data of the Drone (created and
            updated timestamps, dns name, unique id, site_name, machine_type, etc.)
        :type document: AttributeDict
        :return: None
        """
        revision = int(
            self._es.search(
                index=f"{self._index}*",
                body={
                    "query": {"term": {"drone_uuid.keyword": document["drone_uuid"]}}
                },
            )["hits"]["total"]["value"]
        )

        document["revision"] = revision
        self._es.create(
            index=f"{self._index}-{datetime.now().strftime('%Y-%m-%d')}",
            id=f"{document['drone_uuid']}-{revision}",
            body=document,
        )
