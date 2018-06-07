from ..configuration.configuration import Configuration
from ..interfaces.siteadapter import SiteAdapter
from ..utilities.looper import Looper
from CloudStackAIO.CloudStack import CloudStack


class ExoscaleAdapter(SiteAdapter):
    def __init__(self):
        self.configuration = Configuration().CloudStackAIO
        self.cloud_stack_client = CloudStack(end_point=self.configuration['end_point'],
                                             api_key=self.configuration['api_key'],
                                             api_secret=self.configuration['api_secret'],
                                             event_loop=Looper().get_event_loop()
                                             )
        self._site_name = "exoscale"

    async def deploy_resource(self, *args, **kwargs):
        return await self.cloud_stack_client.deployVirtualMachine(serviceofferingid=self.configuration[
            'service_offering_id'],
                                                                  templateid=self.configuration['template_id'],
                                                                  zoneid=self.configuration['zone_id'],
                                                                  keypair='MG',
                                                                  **kwargs)

    @property
    def site_name(self):
        return self._site_name

    async def resource_status(self, *args, **kwargs):
        return await self.cloud_stack_client.listVirtualMachines(**kwargs)

    async def terminate_resource(self, *args, **kwargs):
        return await self.cloud_stack_client.destroyVirtualMachine(**kwargs)
