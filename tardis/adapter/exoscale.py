from ..configuration.configuration import Configuration
from ..exceptions.tardisexceptions import TardisTimeout
from ..exceptions.tardisexceptions import TardisError
from ..exceptions.tardisexceptions import TardisQuotaExceeded
from ..interfaces.siteadapter import ResourceStatus
from ..interfaces.siteadapter import SiteAdapter
from ..utilities.staticmapping import StaticMapping

from cobald.daemon import runtime
from CloudStackAIO.CloudStack import CloudStack
from CloudStackAIO.CloudStack import CloudStackClientException

from contextlib import contextmanager
from datetime import datetime
from functools import partial

import asyncio
import logging


class ExoscaleAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name='exoscale'):
        self.configuration = Configuration().Exoscale
        self.cloud_stack_client = CloudStack(end_point=self.configuration.end_point,
                                             api_key=self.configuration.api_key,
                                             api_secret=self.configuration.api_secret,
                                             event_loop=runtime._meta_runner.runners[asyncio].event_loop
                                             )
        self._machine_type = machine_type
        self._site_name = site_name

        key_translator = StaticMapping(resource_id='id', dns_name='name', created='created',
                                       resource_status='state', updated='created')

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

    async def deploy_resource(self, unique_id):
        response = await self.cloud_stack_client.deployVirtualMachine(name=self.dns_name(unique_id=unique_id),
                                                                      **self.configuration.MachineTypeConfiguration[
                                                                          self._machine_type])
        logging.debug("Exoscale deployVirtualMachine returned {}".format(response))
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
        logging.debug("Exoscale listVirtualMachines returned {}".format(response))
        return self.handle_response(response['virtualmachine'][0])

    async def stop_resource(self, resource_attributes):
        response = await self.cloud_stack_client.stopVirtualMachine(id=resource_attributes.resource_id)
        logging.debug("Exoscale stopVirtualMachine returned {}".format(response))
        return response

    async def terminate_resource(self, resource_attributes):
        response = await self.cloud_stack_client.destroyVirtualMachine(id=resource_attributes.resource_id)
        logging.debug("Exoscale destroyVirtualMachine returned {}".format(response))
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except KeyError as ke:
            if response['errorcode'] == 535:
                raise TardisQuotaExceeded
        except asyncio.TimeoutError as te:
            raise TardisTimeout from te
        except CloudStackClientException as ce:
            raise TardisError from ce
