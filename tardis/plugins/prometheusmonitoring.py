from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin
from ..interfaces.state import State
from ..interfaces.siteadapter import ResourceStatus
from ..utilities.attributedict import AttributeDict

import logging
from prometheus_client import Gauge, start_http_server


class PrometheusMonitoring(Plugin):
    """
    The :py:class:`~tardis.plugins.prometheusmonitoring.PrometheusMonitoring`
    implements an interface to monitor the state of the Drones using Prometheus.
    """

    def __init__(self):
        self.logger = logging.getLogger("prometheusmonitoring")
        self.logger.setLevel(logging.DEBUG)
        config = Configuration().Plugins.PrometheusMonitoring

        self._drones = {}

        self._booting = Gauge("booting", "Booting drones")
        self._running = Gauge("running", "Running drones")
        self._stopped = Gauge("stopped", "Stopped drones")
        self._deleted = Gauge("deleted", "Deleted drones")
        self._error = Gauge("error", "Drones in error state")

        start_http_server(config.port)

    def compute_metrics(self) -> None:
        booting = 0
        running = 0
        stopped = 0
        error = 0
        for drone in self._drones.values():
            if drone.resource_status == ResourceStatus.Booting:
                booting += 1
            if drone.resource_status == ResourceStatus.Running:
                running += 1
            if drone.resource_status == ResourceStatus.Stopped:
                stopped += 1
            if drone.resource_status == ResourceStatus.Error:
                error += 1

        self._booting.set(booting)
        self._running.set(running)
        self._stopped.set(stopped)
        self._error.set(error)

    async def notify(self, state: State, resource_attributes: AttributeDict) -> None:
        """
        Update metrics at every state change

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

        if resource_attributes.resource_status == ResourceStatus.Deleted:
            self._drones.pop(resource_attributes.drone_uuid, None)
            self._deleted.inc()
        else:
            self._drones[resource_attributes.drone_uuid] = resource_attributes

        self.compute_metrics()
