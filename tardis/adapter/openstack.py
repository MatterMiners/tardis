from asyncopenstackclient import AuthPassword
from asyncopenstackclient import NovaClient
from simple_rest_client.exceptions import AuthError
from aiohttp import ClientConnectionError
from ..configuration.configuration import Configuration
from ..exceptions.tardisexceptions import TardisAuthError
from ..exceptions.tardisexceptions import TardisError
from ..exceptions.tardisexceptions import TardisTimeout
from ..exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ..interfaces.siteadapter import ResourceStatus
from ..interfaces.siteadapter import SiteAdapter
from ..utilities.staticmapping import StaticMapping

from asyncio import TimeoutError
from contextlib import contextmanager
from datetime import datetime
from functools import partial

import logging


class OpenStackAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name='otc'):
        self.configuration = getattr(Configuration(), site_name.upper())
        self._machine_type = machine_type
        self._site_name = site_name

        auth = AuthPassword(auth_url=self.configuration.auth_url,
                            username=self.configuration.username,
                            password=self.configuration.password,
                            project_name=self.configuration.project_name,
                            user_domain_name=self.configuration.user_domain_name,
                            project_domain_name=self.configuration.project_domain_name)

        self.nova = NovaClient(session=auth)

        key_translator = StaticMapping(resource_id='id', dns_name='name', resource_status='status')

        translator_functions = StaticMapping(created=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"),
                                             updated=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"),
                                             status=lambda x, translator=StaticMapping(BUILD=ResourceStatus.Booting,
                                                                                       ACTIVE=ResourceStatus.Running,
                                                                                       SHUTOFF=ResourceStatus.Stopped):
                                             translator[x])

        self.handle_response = partial(self.handle_response, key_translator=key_translator,
                                       translator_functions=translator_functions)

    async def deploy_resource(self, unique_id):
        specs = self.configuration.MachineTypeConfiguration[self._machine_type]
        specs['name'] = self.dns_name(unique_id)
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.create(server=specs)
        logging.debug(f"OTC servers servers create returned {response}")
        return self.handle_response(response['server'], dns_name=specs['name'])

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
        logging.debug(f"OTC servers get returned {response}")
        return self.handle_response(response['server'])

    async def stop_resource(self, resource_attributes):
        await self.nova.init_api(timeout=60)
        params = {'os-stop': None}
        response = await self.nova.servers.run_action(resource_attributes.resource_id, **params)
        logging.debug(f"OTC servers stop returned {response}")
        return response

    async def terminate_resource(self, resource_attributes):
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.force_delete(resource_attributes.resource_id)
        logging.debug(f"OTC servers servers terminate returned {response}")
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TimeoutError as te:
            raise TardisTimeout from te
        except AuthError as ae:
            raise TardisAuthError from ae
        except ClientConnectionError:
            logging.info("Connection reset error")
            raise TardisResourceStatusUpdateFailed
        except:
            raise TardisError
