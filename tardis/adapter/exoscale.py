from ..configuration.configuration import Configuration
from ..exceptions.tardisexceptions import TardisTimeout
from ..exceptions.tardisexceptions import TardisError
from ..interfaces.siteadapter import SiteAdapter
from ..utilities.looper import Looper

from CloudStackAIO.CloudStack import CloudStack
from CloudStackAIO.CloudStack import CloudStackClientException

from asyncio import TimeoutError
from contextlib import contextmanager
import logging


class ExoscaleAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name='exoscale'):
        self.configuration = Configuration().Exoscale
        self.cloud_stack_client = CloudStack(end_point=self.configuration.end_point,
                                             api_key=self.configuration.api_key,
                                             api_secret=self.configuration.api_secret,
                                             event_loop=Looper().get_event_loop()
                                             )
        self._machine_type = machine_type
        self._site_name = site_name

    async def deploy_resource(self, unique_id, **kwargs):
        kwargs.update(self.configuration.MachineTypeConfiguration[self._machine_type])
        response = await self.cloud_stack_client.deployVirtualMachine(name=self.dns_name(unique_id=unique_id), **kwargs)
        logging.debug("Exoscale deployVirtualMachine returned {}".format(response))
        return self.handle_response(response)

    def handle_response(self, response):
        translator = dict(machine_id='id', dns_name='name')

        translated_response={}

        for translated_key, key in translator.items():
            translated_response[translated_key] = response['virtualmachine'][key]

        return translated_response

    @property
    def machine_type(self):
        return self._machine_type

    @property
    def site_name(self):
        return self._site_name

    async def resource_status(self, **kwargs):
        response = await self.cloud_stack_client.listVirtualMachines(**kwargs)
        logging.debug("Exoscale listVirtualMachines returned {}".format(response))
        return response

    async def terminate_resource(self, **kwargs):
        response = await self.cloud_stack_client.destroyVirtualMachine(**kwargs)
        logging.debug("Exoscale destroyVirtualMachine returned {}".format(response))
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TimeoutError as te:
            raise TardisTimeout from te
        except CloudStackClientException as ce:
            raise TardisError from ce

