from ...exceptions.tardisexceptions import TardisError
from ...interfaces.siteadapter import ResourceStatus
from ...interfaces.siteadapter import SiteAdapter
from ...utilities.attributedict import AttributeDict
from ...utilities.staticmapping import StaticMapping

from contextlib import contextmanager
from datetime import datetime
from datetime import timedelta
from functools import partial
from uuid import uuid4

import asyncio


class FakeSiteAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str) -> None:
        self._machine_type = machine_type
        self._site_name = site_name
        self._api_response_delay = self.configuration.api_response_delay
        self._resource_boot_time = self.configuration.resource_boot_time

        key_translator = StaticMapping(
            remote_resource_uuid="remote_resource_uuid",
            resource_status="resource_status",
            created="created",
            updated="updated",
            resource_boot_time="resource_boot_time",
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=StaticMapping(),
        )

        self._stopped_n_terminated_resources = {}

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        await asyncio.sleep(self._api_response_delay.get_value())
        now = datetime.now()
        response = AttributeDict(
            remote_resource_uuid=uuid4().hex,
            resource_status=ResourceStatus.Booting,
            created=now,
            updated=now,
            resource_boot_time=self._resource_boot_time.get_value(),
        )
        return self.handle_response(response)

    def get_resource_boot_time(self, resource_attributes: AttributeDict) -> float:
        try:
            return resource_attributes.resource_boot_time
        except AttributeError:
            # In case tardis is restarted, resource_boot_time is not set, so re-set
            resource_boot_time = resource_attributes[
                "resource_boot_time"
            ] = self._resource_boot_time.get_value()
            return resource_boot_time

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        await asyncio.sleep(self._api_response_delay.get_value())
        try:  # check if resource has been stopped or terminated
            resource_status = self._stopped_n_terminated_resources[
                resource_attributes.drone_uuid
            ]
        except KeyError:
            pass
        else:
            return self.handle_response(AttributeDict(resource_status=resource_status))

        created_time = resource_attributes.created

        resource_boot_time = self.get_resource_boot_time(resource_attributes)
        # check if resource is already running
        if (datetime.now() - created_time) > timedelta(seconds=resource_boot_time):
            return self.handle_response(
                AttributeDict(resource_status=ResourceStatus.Running)
            )
        return self.handle_response(resource_attributes)

    async def stop_resource(self, resource_attributes: AttributeDict):
        await asyncio.sleep(self._api_response_delay.get_value())
        self._stopped_n_terminated_resources[
            resource_attributes.drone_uuid
        ] = ResourceStatus.Stopped
        return self.handle_response(
            AttributeDict(resource_status=ResourceStatus.Stopped)
        )

    async def terminate_resource(self, resource_attributes: AttributeDict):
        await asyncio.sleep(self._api_response_delay.get_value())
        self._stopped_n_terminated_resources[
            resource_attributes.drone_uuid
        ] = ResourceStatus.Deleted
        return self.handle_response(
            AttributeDict(resource_status=ResourceStatus.Deleted)
        )

    @contextmanager
    def handle_exceptions(self) -> None:
        try:
            yield
        except Exception as ex:
            raise TardisError from ex
