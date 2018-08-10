from asyncopenstackclient import AuthPassword
from asyncopenstackclient import NovaClient
from simple_rest_client.exceptions import AuthError
from ..configuration.configuration import Configuration
from ..exceptions.tardisexceptions import TardisAuthError
from ..exceptions.tardisexceptions import TardisError
from ..exceptions.tardisexceptions import TardisTimeout
from ..interfaces.siteadapter import ResourceStatus
from ..interfaces.siteadapter import SiteAdapter

from asyncio import TimeoutError
from contextlib import contextmanager
from datetime import datetime
from functools import partial

import logging


class OTCAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name='otc'):
        self.configuration = Configuration().OTC
        self._machine_type = machine_type
        self._site_name = site_name

        auth = AuthPassword(auth_url=self.configuration.auth_url,
                            username=self.configuration.username,
                            password=self.configuration.password,
                            project_name=self.configuration.project_name,
                            user_domain_name=self.configuration.user_domain_name,
                            project_domain_name=self.configuration.project_domain_name)

        self.nova = NovaClient(session=auth)

        key_translator = dict(resource_id='id', dns_name='name', created='created', resource_status='status',
                              updated='updated')

        translator_functions = dict(created=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"),
                                    updated=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"),
                                    status=lambda x: getattr(ResourceStatus, x.title()))

        self.handle_response = partial(self.handle_response, key_translator=key_translator,
                                       translator_functions=translator_functions)

    async def deploy_resource(self, unique_id):
        specs = self.configuration.MachineTypeConfiguration[self._machine_type]
        specs['name'] = self.dns_name(unique_id)
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.create(server=specs)
        logging.debug("OTC servers servers create returned {}".format(response))
        return self.handle_response(response, dns_name=specs['name'])

    @property
    def machine_meta_data(self):
        return self.configuration.MachineMetaData[self._machine_type]

    @property
    def machine_type(self):
        return self._machine_type

    @property
    def site_name(self):
        return self._site_name

    async def resource_status(self, resource_attributes):
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.get(resource_attributes.resource_id)
        logging.debug("OTC servers get returned {}".format(response))
        return self.handle_response(response)

    async def terminate_resource(self, resource_attributes):
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.force_delete(resource_attributes.resource_id)
        logging.debug("OTC servers servers terminate returned {}".format(response))
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TimeoutError as te:
            raise TardisTimeout from te
        except AuthError as ae:
            raise TardisAuthError from ae
        except:
            raise TardisError
