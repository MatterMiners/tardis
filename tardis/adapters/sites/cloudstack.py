from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisQuotaExceeded
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.interfaces.siteadapter import SiteAdapter
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.staticmapping import StaticMapping

from aiohttp import ClientConnectionError
from cobald.daemon import runtime
from CloudStackAIO.CloudStack import CloudStack
from CloudStackAIO.CloudStack import CloudStackClientException

from contextlib import contextmanager
from datetime import datetime
from functools import partial

import asyncio
import logging

logger = logging.getLogger("cobald.runtime.tardis.adapters.sites.cloudstack")


class CloudStackAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str):
        self._machine_type = machine_type
        self._site_name = site_name

        self.cloud_stack_client = CloudStack(
            end_point=self.configuration.end_point,
            api_key=self.configuration.api_key,
            api_secret=self.configuration.api_secret,
            event_loop=runtime._meta_runner.runners[asyncio].event_loop,
        )

        key_translator = StaticMapping(
            remote_resource_uuid="id", drone_uuid="name", resource_status="state"
        )

        translator_functions = StaticMapping(
            created=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z"),
            updated=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z"),
            state=lambda x, translator=StaticMapping(
                Present=ResourceStatus.Booting,
                Running=ResourceStatus.Running,
                Stopped=ResourceStatus.Stopped,
                Expunged=ResourceStatus.Deleted,
                Destroyed=ResourceStatus.Deleted,
            ): translator[x],
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=translator_functions,
        )

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        response = await self.cloud_stack_client.deployVirtualMachine(
            name=resource_attributes.drone_uuid, **self.machine_type_configuration
        )
        logger.debug(f"{self.site_name} deployVirtualMachine returned {response}")
        return self.handle_response(response["virtualmachine"])

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        response = await self.cloud_stack_client.listVirtualMachines(
            id=resource_attributes.remote_resource_uuid
        )
        logger.debug(f"{self.site_name} listVirtualMachines returned {response}")
        return self.handle_response(response["virtualmachine"][0])

    async def stop_resource(self, resource_attributes: AttributeDict):
        response = await self.cloud_stack_client.stopVirtualMachine(
            id=resource_attributes.remote_resource_uuid
        )
        logger.debug(f"{self.site_name} stopVirtualMachine returned {response}")
        return response

    async def terminate_resource(self, resource_attributes: AttributeDict):
        response = await self.cloud_stack_client.destroyVirtualMachine(
            id=resource_attributes.remote_resource_uuid
        )
        logger.debug(f"{self.site_name} destroyVirtualMachine returned {response}")
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except asyncio.TimeoutError as te:
            raise TardisTimeout from te
        except ClientConnectionError:
            logger.warning("Connection reset error")
            raise TardisResourceStatusUpdateFailed
        except CloudStackClientException as ce:
            log_msg = (
                f"Error code: {ce.error_code}, error text: {ce.error_text}, "
                f"response: {ce.response}"
            )
            if ce.error_code == 535:
                logger.warning(f"Quota exceeded: {log_msg}")
                raise TardisQuotaExceeded
            elif ce.error_code == 500:
                if "timed out" in ce.response["message"]:
                    logger.warning(f"Timed out: {log_msg}")
                    raise TardisTimeout from ce
                elif "connection was closed" in ce.response["message"]:
                    logger.warning(f"Connection was closed: {log_msg}")
                    raise TardisResourceStatusUpdateFailed from ce
                else:
                    logger.critical(log_msg)
                    raise TardisError from ce
            else:
                logger.critical(log_msg)
                raise TardisError from ce
