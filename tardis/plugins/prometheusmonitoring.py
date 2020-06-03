from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin
from ..interfaces.state import State
from ..interfaces.siteadapter import ResourceStatus
from ..utilities.attributedict import AttributeDict

import logging
from aioprometheus import Service, Gauge

logger = logging.getLogger("cobald.runtime.tardis.plugins.prometheusmonitoring")


class PrometheusMonitoring(Plugin):
    """
    The :py:class:`~.PrometheusMonitoring`
    implements an interface to monitor the state of the Drones using Prometheus.
    """

    def __init__(self):
        config = Configuration().Plugins.PrometheusMonitoring

        self._port = config.port
        self._addr = config.addr

        self._svr_started = False
        self._drones = {}

        self._svr = Service()

        self._gauges = {
            ResourceStatus.Booting: Gauge("booting", "Booting drones"),
            ResourceStatus.Running: Gauge("running", "Running drones"),
            ResourceStatus.Stopped: Gauge("stopped", "Stopped drones"),
            ResourceStatus.Deleted: Gauge("deleted", "Deleted drones"),
            ResourceStatus.Error: Gauge("error", "Drones in error state"),
        }

        for gauge in self._gauges.values():
            self._svr.register(gauge)
            gauge.set({}, 0)

    async def start(self):
        await self._svr.start(addr=self._addr, port=self._port)
        logger.debug(f"Serving Prometheus metrics on {self._svr.metrics_url}")
        self._svr_started = True

    async def notify(self, state: State, resource_attributes: AttributeDict) -> None:
        """
        Update Prometheus metrics at every state change

        :param state: New state of the Drone
        :type state: State
        :param resource_attributes: Contains all meta-data of the Drone (created and
            updated timestamps, dns name, unique id, site_name, machine_type, etc.)
        :type resource_attributes: AttributeDict
        :return: None
        """
        if not self._svr_started:
            await self.start()

        logger.debug(f"Drone: {str(resource_attributes)} has changed state to {state}")

        if resource_attributes.drone_uuid in self._drones:
            old_status = self._drones[resource_attributes.drone_uuid]
            self._gauges[old_status].dec({})

        new_status = resource_attributes.resource_status
        self._drones[resource_attributes.drone_uuid] = new_status

        self._gauges[new_status].inc({})

        if new_status == ResourceStatus.Deleted:
            self._drones.pop(resource_attributes.drone_uuid, None)
