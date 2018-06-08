from ..configuration.configuration import Configuration
from ..interfaces.siteadapter import SiteAdapter
from ..utilities.looper import Looper
from CloudStackAIO.CloudStack import CloudStack

import logging


class ExoscaleAdapter(SiteAdapter):
    def __init__(self, site_name='exoscale'):
        self.configuration = Configuration().Exoscale
        self.cloud_stack_client = CloudStack(end_point=self.configuration['end_point'],
                                             api_key=self.configuration['api_key'],
                                             api_secret=self.configuration['api_secret'],
                                             event_loop=Looper().get_event_loop()
                                             )
        self._site_name = site_name

    async def deploy_resource(self, *args, **kwargs):
        response = await self.cloud_stack_client.deployVirtualMachine(serviceofferingid=self.configuration[
            'service_offering_id'],
                                                                  templateid=self.configuration['template_id'],
                                                                  zoneid=self.configuration['zone_id'],
                                                                  keypair='MG',
                                                                  **kwargs)
        logging.debug("Exoscale deployVirtualMachine returned {}".format(response))
        return response

    @property
    def site_name(self):
        return self._site_name

    async def resource_status(self, *args, **kwargs):
        response = await self.cloud_stack_client.listVirtualMachines(**kwargs)
        logging.debug("Exoscale listVirtualMachines returned {}".format(response))
        return response

    async def terminate_resource(self, *args, **kwargs):
        response = await self.cloud_stack_client.destroyVirtualMachine(**kwargs)
        logging.debug("Exoscale destroyVirtualMachine returned {}".format(response))
        return response
