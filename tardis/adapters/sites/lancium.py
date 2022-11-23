from aiolancium.client import Authenticator, LanciumClient

from ...exceptions.tardisexceptions import TardisError, TardisResourceStatusUpdateFailed
from ...interfaces.siteadapter import SiteAdapter, ResourceStatus
from ...utilities.attributedict import AttributeDict, convert_to_attribute_dict
from ...utilities.asynccachemap import AsyncCacheMap
from ...utilities.staticmapping import StaticMapping

from contextlib import contextmanager
from datetime import datetime
from functools import partial
from typing import Dict

import logging

logger = logging.getLogger("cobald.runtime.tardis.adapters.sites.lancium")


async def lancium_status_updater(client: LanciumClient) -> Dict:
    response = await client.jobs.show_jobs()
    logger.debug(f"Show jobs returned {response}")
    return {job["id"]: job for job in response["jobs"]}


class LanciumAdapter(SiteAdapter):
    # space in last key requires dict expansion in `__init__` `translation_functions`
    resource_status_translation = {
        "created": ResourceStatus.Booting,
        "submitted": ResourceStatus.Booting,
        "queued": ResourceStatus.Booting,
        "ready": ResourceStatus.Booting,
        "running": ResourceStatus.Running,
        "error": ResourceStatus.Error,
        "finished": ResourceStatus.Stopped,
        "delete pending": ResourceStatus.Stopped,
        "deleted": ResourceStatus.Deleted,
    }

    def __init__(self, machine_type: str, site_name: str):
        self._machine_type = machine_type
        self._site_name = site_name

        auth = Authenticator(api_key=self.configuration.api_key)
        self.client = LanciumClient(api_url=self.configuration.api_url, auth=auth)

        key_translator = StaticMapping(
            remote_resource_uuid="id",
            drone_uuid="name",
            resource_status="status",
        )

        translator_functions = StaticMapping(
            status=lambda x, translator=StaticMapping(
                **self.resource_status_translation
            ): translator[x],
            id=int,
            name=str,
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=translator_functions,
        )

        self._lancium_status = AsyncCacheMap(
            update_coroutine=partial(lancium_status_updater, self.client),
            max_age=self.configuration.max_age * 60,
        )

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        specs = dict(name=resource_attributes.drone_uuid)
        specs["resources"] = dict(
            core_count=self.machine_meta_data.Cores,
            memory=self.machine_meta_data.Memory,
            scratch=self.machine_meta_data.Disk,
        )
        specs["environment"] = [
            {"variable": f"TardisDrone{key}", "value": str(value)}
            for key, value in self.drone_environment(
                resource_attributes.drone_uuid,
                resource_attributes.obs_machine_meta_data_translation_mapping,
            ).items()
        ]
        specs.update(self.machine_type_configuration)
        create_response = await self.client.jobs.create_job(job=specs)
        logger.debug(f"{self.site_name} create job returned {create_response}")
        submit_response = await self.client.jobs.submit_job(
            id=create_response["job"]["id"]
        )
        logger.debug(f"{self.site_name} submit job returned {submit_response}")
        return self.handle_response(create_response["job"])

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        await self._lancium_status.update_status()
        # In case the created timestamp is after last update timestamp of the
        # asynccachemap, no decision about the current state can be given,
        # since map is updated asynchronously.
        try:
            resource_uuid = resource_attributes.remote_resource_uuid
            resource_status = self._lancium_status[resource_uuid]
        except KeyError as err:
            if (
                self._lancium_status.last_update - resource_attributes.created
            ).total_seconds() < 0:
                raise TardisResourceStatusUpdateFailed from err
            else:
                resource_status = {
                    "id": resource_attributes.remote_resource_uuid,
                    "status": "deleted",
                }
        logger.debug(f"{self.site_name} has status {resource_status}.")
        resource_attributes["updated"]=datetime.now()
        return convert_to_attribute_dict(
            {**resource_attributes, **self.handle_response(resource_status)}
        )

    async def stop_resource(self, resource_attributes: AttributeDict):
        response = await self.client.jobs.terminate_job(
            id=resource_attributes.remote_resource_uuid
        )
        logger.debug(f"{self.site_name} stop resource returned {response}")
        return response

    async def terminate_resource(self, resource_attributes: AttributeDict):
        response = await self.client.jobs.delete_job(
            id=resource_attributes.remote_resource_uuid
        )
        logger.debug(f"{self.site_name} terminate resource returned {response}")
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except Exception as ex:
            raise TardisError from ex
