from asyncopenstackclient import AuthPassword
from asyncopenstackclient import NovaClient
from simple_rest_client.exceptions import AuthError
from simple_rest_client.exceptions import ClientError
from aiohttp import ClientConnectionError
from aiohttp import ContentTypeError

from tardis.exceptions.tardisexceptions import TardisAuthError
from tardis.exceptions.tardisexceptions import TardisDroneCrashed
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.interfaces.siteadapter import SiteAdapter
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.staticmapping import StaticMapping

from asyncio import TimeoutError
from contextlib import contextmanager
from datetime import datetime
from functools import partial

import logging

logger = logging.getLogger("cobald.runtime.tardis.adapters.sites.openstack")


class OpenStackAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str):
        self._machine_type = machine_type
        self._site_name = site_name

        auth = AuthPassword(
            auth_url=self.configuration.auth_url,
            username=self.configuration.username,
            password=self.configuration.password,
            project_name=self.configuration.project_name,
            user_domain_name=self.configuration.user_domain_name,
            project_domain_name=self.configuration.project_domain_name,
        )

        self.nova = NovaClient(session=auth)

        key_translator = StaticMapping(
            remote_resource_uuid="id", drone_uuid="name", resource_status="status"
        )

        translator_functions = StaticMapping(
            created=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"),
            updated=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"),
            status=lambda x, translator=StaticMapping(
                BUILD=ResourceStatus.Booting,
                ACTIVE=ResourceStatus.Running,
                SHUTOFF=ResourceStatus.Stopped,
                ERROR=ResourceStatus.Error,
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
        specs = dict(name=resource_attributes.drone_uuid)
        specs.update(self.machine_type_configuration)
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.create(server=specs)
        logger.debug(f"{self.site_name} servers create returned {response}")
        return self.handle_response(response["server"])

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.get(resource_attributes.remote_resource_uuid)
        logger.debug(f"{self.site_name} servers get returned {response}")
        return self.handle_response(response["server"])

    async def stop_resource(self, resource_attributes: AttributeDict):
        await self.nova.init_api(timeout=60)
        params = {"os-stop": None}
        response = await self.nova.servers.run_action(
            resource_attributes.remote_resource_uuid, **params
        )
        logger.debug(f"{self.site_name} servers stop returned {response}")
        return response

    async def terminate_resource(self, resource_attributes: AttributeDict):
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.force_delete(
            resource_attributes.remote_resource_uuid
        )
        logger.debug(f"{self.site_name} servers terminate returned {response}")
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TimeoutError as te:
            raise TardisTimeout from te
        except AuthError as ae:
            raise TardisAuthError from ae
        except ContentTypeError:
            logger.warning("OpenStack: content Type Error")
            raise TardisResourceStatusUpdateFailed
        except ClientError:
            logger.warning("REST client error")
            raise TardisDroneCrashed
        except ClientConnectionError:
            logger.warning("Connection reset error")
            raise TardisResourceStatusUpdateFailed
        except Exception as ex:
            raise TardisError from ex
