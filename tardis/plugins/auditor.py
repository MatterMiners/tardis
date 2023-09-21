from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin
from ..interfaces.state import State
from ..utilities.attributedict import AttributeDict
from ..resources.dronestates import AvailableState, DownState

import pyauditor

import datetime
import logging
from tzlocal import get_localzone


class Auditor(Plugin):
    """
    The :py:class:`~tardis.plugins.auditor.Auditor` plugin is a collector for the
    accounting tool Auditor. It sends accounting information of individual drones to an
    Auditor instance. The records contain information about the provided resources of
    the drones as well as start and stop times. When a drone enters `AvailableState`, a
    record with the start time set to the time it went into this state is stored in the
    Auditor database. The stop time remains empty until the drone goes into `DownState`.
    The Auditor plugin does not keep any state.
    """

    def __init__(self):
        self.logger = logging.getLogger("cobald.runtime.tardis.plugins.auditor")
        config = Configuration()
        config_auditor = config.Plugins.Auditor

        self._resources = {}
        self._components = {}
        for site in config.Sites:
            self._resources[site.name] = {}
            self._components[site.name] = {}
            for machine_type in getattr(config, site.name).MachineTypes:
                self._resources[site.name][machine_type] = {}
                self._components[site.name][machine_type] = {}
                for resource in getattr(config, site.name).MachineMetaData[
                    machine_type
                ]:
                    self._resources[site.name][machine_type][resource] = getattr(
                        config, site.name
                    ).MachineMetaData[machine_type][resource]
                    try:
                        self._components[site.name][machine_type][resource] = getattr(
                            config_auditor.components, machine_type
                        ).get(resource, {})
                    except AttributeError:
                        continue

        self._user = getattr(config_auditor, "user", "tardis")
        self._group = getattr(config_auditor, "group", "tardis")
        auditor_timeout = getattr(config_auditor, "timeout", 30)
        self._local_timezone = get_localzone()
        self._client = (
            pyauditor.AuditorClientBuilder()
            .address(config_auditor.host, config_auditor.port)
            .timeout(auditor_timeout)
            .build()
        )

    async def notify(self, state: State, resource_attributes: AttributeDict) -> None:
        """
        Pushes a record to an Auditor instance when the drone is in state
        `AvailableState` or `DownState`.

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

        if isinstance(state, AvailableState):
            record = self.construct_record(resource_attributes)
            await self._client.add(record)
        elif isinstance(state, DownState):
            record = self.construct_record(resource_attributes)
            record.with_stop_time(
                resource_attributes["updated"]
                .replace(tzinfo=self._local_timezone)
                .astimezone(datetime.timezone.utc)
            )
            try:
                await self._client.update(record)
            except RuntimeError as e:
                if str(e).startswith(
                    "Reqwest Error: HTTP status client error (404 Not Found)"
                ):
                    self.logger.debug(
                        f"Could not update record {record.record_id}, "
                        "it probably does not exist in the database"
                    )
                else:
                    raise

    def construct_record(self, resource_attributes: AttributeDict):
        """
        Constructs a record from ``resource_attributes``.

        :param resource_attributes: Contains all meta-data of the Drone (created and
            updated timestamps, dns name, unique id, site_name, machine_type, etc.)
        :type resource_attributes: AttributeDict
        :return: Record
        """
        meta = (
            pyauditor.Meta()
            .insert("site_id", [resource_attributes["site_name"]])
            .insert("user_id", [self._user])
            .insert("group_id", [self._group])
        )
        record = pyauditor.Record(
            resource_attributes["drone_uuid"],
            resource_attributes["updated"]
            .replace(tzinfo=self._local_timezone)
            .astimezone(datetime.timezone.utc),
        ).with_meta(meta)

        for resource, amount in self._resources[resource_attributes["site_name"]][
            resource_attributes["machine_type"]
        ].items():
            component = pyauditor.Component(resource, amount)
            for score_name, score_val in self._components[
                resource_attributes["site_name"]
            ][resource_attributes["machine_type"]][resource].items():
                component = component.with_score(pyauditor.Score(score_name, score_val))

            record = record.with_component(component)

        return record
