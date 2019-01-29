from ..configuration.configuration import Configuration
from ..exceptions.tardisexceptions import TardisError
from ..exceptions.tardisexceptions import TardisTimeout
from ..exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ..interfaces.siteadapter import ResourceStatus
from ..interfaces.siteadapter import SiteAdapter
from ..utilities.staticmapping import StaticMapping

from asyncio import TimeoutError
from contextlib import contextmanager
from functools import partial
from datetime import datetime

import asyncssh
import logging
import re


class MoabAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name):
        self.configuration = getattr(Configuration(), site_name)
        self._machine_type = machine_type
        self._site_name = site_name

        # get authentification
        self._remote_host = self.configuration.remote_host
        self._login = self.configuration.login
        self._key = self.configuration.key

        key_translator = StaticMapping(resource_id='SystemJID', resource_status='State')

        translator_functions = StaticMapping(State=lambda x, translator=StaticMapping(Idle=ResourceStatus.Booting,
                                                                                      Running=ResourceStatus.Running,
                                                                                      Completed=ResourceStatus.Stopped,
                                                                                      Canceling=ResourceStatus.Error,
                                                                                      Vacated=ResourceStatus.Error):
                                             translator[x],
                                             SystemJID=lambda x: int(x))

        self.handle_response = partial(self.handle_response, key_translator=key_translator,
                                       translator_functions=translator_functions)

    async def deploy_resource(self, resource_attributes):
        async with asyncssh.connect(self._remote_host, username=self._login, client_keys=[self._key]) as conn:
            request_command = f'msub -j oe -m p -l walltime={self.machine_meta_data.Walltime},' \
                f'mem={self.machine_meta_data.Memory},nodes={self.machine_meta_data.NodeType} ' \
                f'{self.machine_meta_data.StartupCommand}'
            result = await conn.run(request_command, check=True)
            logging.debug(f"{self.site_name} servers create returned {result}")
            try:
                resource_id = int(result.stdout)
                resource_attributes.update(resource_id=resource_id, created=datetime.now(), updated=datetime.now(),
                                           dns_name=self.dns_name(resource_id), resource_status=ResourceStatus.Booting)
                return resource_attributes
            except:
                raise TardisError

    @property
    def machine_meta_data(self):
        return self.configuration.MachineMetaData[self._machine_type]

    @property
    def machine_type(self):
        return self._machine_type

    @property
    def site_name(self):
        return self._site_name

    def dns_name(self, resource_id):
        return f'{self.site_name}-{resource_id}'

    async def resource_status(self, resource_attributes):
        async with asyncssh.connect(self._remote_host, username=self._login, client_keys=[self._key]) as conn:
            status_command = f'checkjob {resource_attributes.resource_id}'
            response = await conn.run(status_command, check=True)
        pattern = re.compile(r'^(.*):\s+(.*)$', flags=re.MULTILINE)
        response = dict(pattern.findall(response.stdout))
        logging.debug(f'{self.site_name} has status {response}.')
        resource_attributes.update(updated=datetime.now())
        return self.handle_response(response, **resource_attributes)

    async def terminate_resource(self, resource_attributes):
        async with asyncssh.connect(self._remote_host, username=self._login, client_keys=[self._key]) as conn:
            request_command = f"canceljob {resource_attributes.resource_id}"
            response = await conn.run(request_command, check=True)
        pattern = re.compile(r'^job \'(\d*)\' cancelled', flags=re.MULTILINE)
        logging.debug(f"{self.site_name} servers terminate returned {response}")
        resource_id = int(pattern.findall(response.stdout)[0])
        if resource_id != resource_attributes.resource_id:
            raise TardisError(f'Failed to terminate {resource_attributes.resource_id}.')
        resource_attributes.update(resource_status=ResourceStatus.Stopped, updated=datetime.now())
        return self.handle_response({'SystemJID': resource_id}, **resource_attributes)

    async def stop_resource(self, resource_attributes):
        logging.debug('MOAB jobs cannot be stopped gracefully. Terminating instead.')
        return await self.terminate_resource(resource_attributes)

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TimeoutError as te:
            raise TardisTimeout from te
        except asyncssh.Error as exc:
            logging.info('SSH connection failed: ' + str(exc))
            raise TardisResourceStatusUpdateFailed
        except:
            raise TardisError
