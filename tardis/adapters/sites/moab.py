from tardis.configuration.configuration import Configuration
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.interfaces.siteadapter import SiteAdapter
from tardis.utilities.staticmapping import StaticMapping
from tardis.utilities.attributedict import convert_to_attribute_dict

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
        self._startup_command = self.configuration.StartupCommand

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
            request_command = f'msub -j oe -m p -l ' \
                              f'walltime={self.configuration.MachineTypeConfiguration[self._machine_type].Walltime},' \
                              f'mem={self.machine_meta_data.Memory}gb,' \
                              f'nodes={self.configuration.MachineTypeConfiguration[self._machine_type].NodeType} ' \
                              f'{self._startup_command}'
            result = await conn.run(request_command, check=True)
            logging.debug(f"{self.site_name} servers create returned {result}")

            resource_id = int(result.stdout)
            resource_attributes.update(resource_id=resource_id, created=datetime.now(), updated=datetime.now(),
                                       dns_name=self.dns_name(resource_id), resource_status=ResourceStatus.Booting)
            return resource_attributes

    @property
    def machine_meta_data(self):
        return self.configuration.MachineMetaData[self._machine_type]

    @property
    def machine_type(self):
        return self._machine_type

    @property
    def site_name(self):
        return self._site_name

    def check_resource_id(self, resource_attributes, regex, response):
        pattern = re.compile(regex, flags=re.MULTILINE)
        resource_id = int(pattern.findall(response)[0])
        if resource_id != int(resource_attributes.resource_id):
            raise TardisError(f'Failed to terminate {resource_attributes.resource_id}.')
        else:
            resource_attributes.update(resource_status=ResourceStatus.Stopped, updated=datetime.now())
        return resource_id

    async def resource_status(self, resource_attributes):
        async with asyncssh.connect(self._remote_host, username=self._login, client_keys=[self._key]) as conn:
            status_command = f'checkjob {resource_attributes.resource_id}'
            response = await conn.run(status_command, check=True)
        pattern = re.compile(r'^(.*):\s+(.*)$', flags=re.MULTILINE)
        response = dict(pattern.findall(response.stdout))
        response["State"] = response["State"].rstrip()
        logging.debug(f'{self.site_name} has status {response}.')
        resource_attributes.update(updated=datetime.now())
        return convert_to_attribute_dict({**resource_attributes, **self.handle_response(response)})

    async def terminate_resource(self, resource_attributes):
        async with asyncssh.connect(self._remote_host, username=self._login, client_keys=[self._key]) as conn:
            request_command = f"canceljob {resource_attributes.resource_id}"
            response = await conn.run(request_command)
        logging.debug(f"{self.site_name} servers terminate returned {response}")
        if response.exit_status == 0:
            resource_id = self.check_resource_id(resource_attributes, r'^job \'(\d*)\' cancelled', response.stdout)
        elif response.exit_status == 1:
            resource_id = self.check_resource_id(resource_attributes, r'ERROR:  invalid job specified \((\d*)\)',
                                                 response.stderr)
        else:
            raise asyncssh.ProcessError(command=request_command, stdout=response.stdout)

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
        except IndexError as ide:
            raise TardisResourceStatusUpdateFailed from ide
        except Exception as ex:
            raise TardisError from ex
