from asyncopenstackclient import AuthPassword
from asyncopenstackclient import NovaClient
from simple_rest_client.exceptions import AuthError
from simple_rest_client.exceptions import ClientError
from aiohttp import ClientConnectionError
from aiohttp import ContentTypeError
from pydantic import AnyHttpUrl, root_validator

from tardis.exceptions.tardisexceptions import TardisAuthError
from tardis.exceptions.tardisexceptions import TardisDroneCrashed
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import (
    ResourceStatus,
    SiteAdapter,
    SiteAdapterBaseModel,
)
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.staticmapping import StaticMapping

from asyncio import TimeoutError
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from typing import Any, Dict, Optional

import logging

logger = logging.getLogger("cobald.runtime.tardis.adapters.sites.openstack")


class OpenStackAdapterConfigurationModel(SiteAdapterBaseModel):
    """
    pydantic model for the input validation of the OpenStack site adapter configuration
    """

    auth_url: AnyHttpUrl
    username: Optional[str] = None
    password: Optional[str] = None
    project_name: Optional[str] = None
    user_domain_name: Optional[str] = None
    project_domain_name: Optional[str] = None
    application_credential_id: Optional[str] = None
    application_credential_secret: Optional[str] = None

    class Config:
        extra = "forbid"

    @root_validator
    def validate_openstack_config(
        cls, values: Dict[str, Any]  # noqa B902
    ) -> Dict[str, Any]:
        username = values.get("username")
        password = values.get("password")
        project_name = values.get("project_name")
        user_domain_name = values.get("user_domain_name")
        project_domain_name = values.get("project_domain_name")
        application_credential_id = values.get("application_credential_id")
        application_credential_secret = values.get("application_credential_secret")

        def check_option_group_exclusivity(option_group1, option_group2):
            return (
                all(value is not None for value in option_group1)
                and all(value is None for value in option_group2)
            ) or (
                all(value is not None for value in option_group2)
                and all(value is None for value in option_group1)
            )

        if not check_option_group_exclusivity(
            option_group1=(application_credential_id, application_credential_secret),
            option_group2=(
                username,
                password,
                project_name,
                user_domain_name,
                project_domain_name,
            ),
        ):
            raise ValueError(
                "OpenStackAdapter exclusively requires either"
                "(application_credential_id, application_credential_secret) or "
                "(username, password, project_name, user_domain_name,"
                "project_domain_name) to be set."
            )
        return values


class OpenStackAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str):
        self._machine_type = machine_type
        self._site_name = site_name
        self._configuration_validation_model = OpenStackAdapterConfigurationModel

        auth = AuthPassword(
            auth_url=self.configuration.auth_url,
            username=self.configuration.username,
            project_name=self.configuration.project_name,
            user_domain_name=self.configuration.user_domain_name,
            project_domain_name=self.configuration.project_domain_name,
            application_credential_id=self.configuration.application_credential_id,
            application_credential_secret=self.configuration.application_credential_secret,  # noqa B950
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
        except ContentTypeError as cte:
            logger.warning("OpenStack: content Type Error")
            raise TardisResourceStatusUpdateFailed from cte
        except ClientError as ce:
            logger.warning("REST client error")
            raise TardisDroneCrashed from ce
        except ClientConnectionError as cde:
            logger.warning("Connection reset error")
            raise TardisResourceStatusUpdateFailed from cde
        except Exception as ex:
            raise TardisError from ex
