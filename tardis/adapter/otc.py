from asyncopenstackclient import AuthPassword
from asyncopenstackclient import NovaClient
from ..configuration.configuration import Configuration
from ..exceptions.tardisexceptions import TardisTimeout
from ..exceptions.tardisexceptions import TardisError
from ..interfaces.siteadapter import SiteAdapter

from asyncio import TimeoutError
from contextlib import contextmanager

import logging


class OTCAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name='otc'):
        self.configuration = Configuration().OTC
        self._machine_type = machine_type
        self._site_name = site_name

        auth = AuthPassword(auth_url=self.configuration.auth_url,
                            username = self.configuration.username,
                            password = self.configuration.password,
                            project_name = self.configuration.project_name,
                            user_domain_name = self.configuration.user_domain_name,
                            project_domain_name = self.configuration.project_domain_name)

        self.nova = NovaClient(session=auth)

    async def deploy_resource(self, unique_id, **kwargs):
        kwargs.update(self.configuration.MachineTypeConfiguration[self._machine_type])
        kwargs['name'] = 'tardis-{}-{}.{}'.format(unique_id, self.machine_type, self.site_name)
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.create(server=kwargs)
        logging.debug("OTC servers servers create returned {}".format(response))
        return self.handle_response(response, dns_name=kwargs['name'])

    def handle_response(self, response, **kwargs):
        translator = dict(machine_id='id')

        translated_response = {}

        for translated_key, key in translator.items():
            translated_response[translated_key] = response['server'][key]

        for key, value in kwargs.items():
            translated_response[key] = value

        return translated_response

    @property
    def machine_type(self):
        return self._machine_type

    @property
    def site_name(self):
        return self._site_name

    async def resource_status(self, **kwargs):
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.list(**kwargs)
        logging.debug("OTC servers list returned {}".format(response))
        return response

    async def terminate_resource(self, **kwargs):
        await self.nova.init_api(timeout=60)
        response = await self.nova.servers.force_delete(kwargs['id'])
        logging.debug("OTC servers servers create returned {}".format(response))
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TimeoutError as te:
            raise TardisTimeout from te