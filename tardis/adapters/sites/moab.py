from ...configuration.configuration import Configuration
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...exceptions.tardisexceptions import TardisError
from ...exceptions.tardisexceptions import TardisTimeout
from ...exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ...interfaces.siteadapter import ResourceStatus
from ...interfaces.siteadapter import SiteAdapter
from ...utilities.staticmapping import StaticMapping
from ...utilities.attributedict import convert_to_attribute_dict
from ...utilities.executors.shellexecutor import ShellExecutor

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

        self._executor = getattr(self.configuration, 'executor', ShellExecutor())

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
        request_command = f'msub -j oe -m p -l ' \
                          f'walltime={self.configuration.MachineTypeConfiguration[self._machine_type].Walltime},' \
                          f'mem={self.machine_meta_data.Memory}gb,' \
                          f'nodes={self.configuration.MachineTypeConfiguration[self._machine_type].NodeType} ' \
                          f'{self._startup_command}'
        result = await self._executor.run_command(request_command)
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

    @staticmethod
    def check_resource_id(resource_attributes, regex, response):
        pattern = re.compile(regex, flags=re.MULTILINE)
        resource_id = int(pattern.findall(response)[0])
        if resource_id != int(resource_attributes.resource_id):
            raise TardisError(f'Failed to terminate {resource_attributes.resource_id}.')
        else:
            resource_attributes.update(resource_status=ResourceStatus.Stopped, updated=datetime.now())
        return resource_id

    async def resource_status(self, resource_attributes):
        status_command = f'checkjob {resource_attributes.resource_id}'
        response = await self._executor.run_command(status_command)
        pattern = re.compile(r'^(.*):\s+(.*)$', flags=re.MULTILINE)
        response = dict(pattern.findall(response.stdout))
        response["State"] = response["State"].rstrip()
        logging.debug(f'{self.site_name} has status {response}.')
        resource_attributes.update(updated=datetime.now())
        return convert_to_attribute_dict({**resource_attributes, **self.handle_response(response)})

    async def terminate_resource(self, resource_attributes):
        request_command = f"canceljob {resource_attributes.resource_id}"
        try:
            response = await self._executor.run_command(request_command)
        except CommandExecutionFailure as cf:
            if cf.exit_code == 1:
                logging.debug(f"{self.site_name} servers terminate returned {cf.stdout}")
                resource_id = self.check_resource_id(resource_attributes, r'ERROR:  invalid job specified \((\d*)\)',
                                                     cf.stderr)
            else:
                raise cf
        else:
            logging.debug(f"{self.site_name} servers terminate returned {response}")
            resource_id = self.check_resource_id(resource_attributes, r'^job \'(\d*)\' cancelled', response.stdout)

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
