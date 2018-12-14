from ..configuration.configuration import Configuration
from ..exceptions.tardisexceptions import TardisTimeout
from ..exceptions.tardisexceptions import TardisError
from ..exceptions.tardisexceptions import TardisQuotaExceeded
from ..exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ..interfaces.siteadapter import ResourceStatus
from ..interfaces.siteadapter import SiteAdapter
from ..utilities.staticmapping import StaticMapping

from aiohttp import ClientConnectionError
from cobald.daemon import runtime
from CloudStackAIO.CloudStack import CloudStack
from CloudStackAIO.CloudStack import CloudStackClientException

from contextlib import contextmanager
from datetime import datetime
from functools import partial

import asyncio
import logging


class CloudStackAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name):
        self.configuration = getattr(Configuration(), site_name.upper())
        self.cloud_stack_client = CloudStack(end_point=self.configuration.end_point,
                                             api_key=self.configuration.api_key,
                                             api_secret=self.configuration.api_secret,
                                             event_loop=runtime._meta_runner.runners[asyncio].event_loop
                                             )
        self._machine_type = machine_type
        self._site_name = site_name

        key_translator = StaticMapping(resource_id='id', dns_name='name', resource_status='state')

        translator_functions = StaticMapping(created=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z"),
                                             updated=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z"),
                                             state=lambda x, translator=StaticMapping(Present=ResourceStatus.Booting,
                                                                                      Running=ResourceStatus.Running,
                                                                                      Stopped=ResourceStatus.Stopped,
                                                                                      Expunged=ResourceStatus.Deleted,
                                                                                      Destroyed=ResourceStatus.Deleted):
                                             translator[x])

        self.handle_response = partial(self.handle_response, key_translator=key_translator,
                                       translator_functions=translator_functions)

    async def deploy_resource(self, resource_attributes):
        response = await self.cloud_stack_client.deployVirtualMachine(name=resource_attributes.dns_name,
                                                                      **self.configuration.MachineTypeConfiguration[
                                                                          self._machine_type])
        logging.debug(f"{self.site_name} deployVirtualMachine returned {response}")
        return self.handle_response(response['virtualmachine'])

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
        response = await self.cloud_stack_client.listVirtualMachines(id=resource_attributes.resource_id)
        logging.debug(f"{self.site_name} listVirtualMachines returned {response}")
        return self.handle_response(response['virtualmachine'][0])

    async def stop_resource(self, resource_attributes):
        response = await self.cloud_stack_client.stopVirtualMachine(id=resource_attributes.resource_id)
        logging.debug(f"{self.site_name} stopVirtualMachine returned {response}")
        return response

    async def terminate_resource(self, resource_attributes):
        response = await self.cloud_stack_client.destroyVirtualMachine(id=resource_attributes.resource_id)
        logging.debug(f"{self.site_name} destroyVirtualMachine returned {response}")
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except asyncio.TimeoutError as te:
            raise TardisTimeout from te
        except ClientConnectionError:
            logging.info("Connection reset error")
            raise TardisResourceStatusUpdateFailed
        except CloudStackClientException as ce:
            if ce.error_code == 535:
                logging.info("Quota exceeded")
                logging.debug(ce.message)
                raise TardisQuotaExceeded
            else:
                raise TardisError from ce
