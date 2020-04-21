from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin
from ..interfaces.state import State
from ..utilities.attributedict import AttributeDict

from concurrent.futures import ThreadPoolExecutor
import logging
import asyncio
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConflictError
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
        self.logger.setLevel(logging.DEBUG)
        config = Configuration().Plugins.ElasticsearchMonitoring

        self._index = config.index + "-" + datetime.now().strftime("%Y-%m-%d")
        self._host = config.host
        self._port = config.port
        self._meta = config.meta

        self._es = Elasticsearch([{"host": self._host, "port": self._port}])

        self.thread_pool_executor = ThreadPoolExecutor(max_workers=1)

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

        resource_attributes = {
            **resource_attributes,
            "state": str(state),
            "meta": self._meta,
            "timestamp": int(time() * 1000),
            "resource_status": str(resource_attributes["resource_status"]),
        }

        await self.async_execute(resource_attributes)

    async def async_execute(self, resource_attributes: AttributeDict) -> None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool_executor, self.execute, resource_attributes
        )

    def execute(self, resource_attributes: AttributeDict) -> None:
        """
        Pushes drone info to an ElasticSearch instance.

        :param state: New state of the Drone
        :type state: State
        :param resource_attributes: Contains all meta-data of the Drone (created and
            updated timestamps, dns name, unique id, site_name, machine_type, etc.)
        :type resource_attributes: AttributeDict
        :return: None
        """
        revision = 0
        while True:
            try:
                # Add revision number
                resource_attributes["revision"] = revision
                doc_id = resource_attributes["drone_uuid"] + "-" + str(revision)
                self._es.create(index=self._index, id=doc_id, body=resource_attributes)
                break
            except ConflictError:
                revision += 1
