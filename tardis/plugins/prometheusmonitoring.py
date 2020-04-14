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

        if resource_attributes.drone_uuid in self._drones:
            old_status = self._drones[resource_attributes.drone_uuid].resource_status
            if old_status == ResourceStatus.Booting:
                self._booting.dec()
            elif old_status == ResourceStatus.Running:
                self._running.dec()
            elif old_status == ResourceStatus.Stopped:
                self._stopped.dec()
            elif old_status == ResourceStatus.Error:
                self._error.dec()

        new_status = resource_attributes.resource_status
        self._drones[resource_attributes.drone_uuid] = resource_attributes

        if new_status == ResourceStatus.Booting:
            self._booting.inc()
        elif new_status == ResourceStatus.Running:
            self._running.inc()
        elif new_status == ResourceStatus.Stopped:
            self._stopped.inc()
        elif new_status == ResourceStatus.Error:
            self._error.inc()
        elif new_status == ResourceStatus.Deleted:
            self._drones.pop(resource_attributes.drone_uuid, None)
            self._deleted.inc()
