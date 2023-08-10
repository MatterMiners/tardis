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
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=StaticMapping(),
        )

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        await asyncio.sleep(self._api_response_delay.get_value())
        response = AttributeDict(
            remote_resource_uuid=uuid4().hex,
            resource_status=ResourceStatus.Booting,
        )
        return self.handle_response(response)

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        await asyncio.sleep(self._api_response_delay.get_value())
        created_time = resource_attributes.created

        resource_boot_time = self._resource_boot_time.get_value()
        # check if resource should already run
        if (datetime.now() - created_time) > timedelta(
            seconds=resource_boot_time
        ) and resource_attributes.get(
            "resource_status",
            ResourceStatus.Booting
            # When cobald is restarted, "resource_status" is not set. Since this is a
            # FakeAdapter, when can safely start the cycle again by assuming
            # ResourceStatus.Booting and let TARDIS manage the drone's life cycle
        ) is ResourceStatus.Booting:
            return self.handle_response(
                AttributeDict(resource_status=ResourceStatus.Running)
            )
        return AttributeDict()  # do not change anything

    async def stop_resource(self, resource_attributes: AttributeDict) -> None:
        await asyncio.sleep(self._api_response_delay.get_value())
        # update resource status manually to ResourceStatus.Stopped, so that
        # the life cycle comes to an end.
        resource_attributes.resource_status = ResourceStatus.Stopped

    async def terminate_resource(self, resource_attributes: AttributeDict) -> None:
        await asyncio.sleep(self._api_response_delay.get_value())
        # update resource status manually to ResourceStatus.Deleted, so that
        # the life cycle is ended.
        resource_attributes.resource_status = ResourceStatus.Deleted

    @contextmanager
    def handle_exceptions(self) -> None:
        try:
            yield
        except Exception as ex:
            raise TardisError from ex
