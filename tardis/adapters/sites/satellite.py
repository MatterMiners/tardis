from tardis.interfaces.siteadapter import SiteAdapter
from tardis.utilities.attributedict import AttributeDict

from contextlib import contextmanager

from tardis.exceptions.tardisexceptions import TardisAuthError
from tardis.exceptions.tardisexceptions import TardisDroneCrashed
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed

import requests
import logging
import yaml
import aiohttp
import ssl

logger = logging.getLogger("cobald.runtime.tardis.interfaces.site")


class SatelliteClient:
    def __init__(self, host_fqdn: str, site_name: str = "satellite.scc.kit.edu"):
        with open("/home/jr4238/satellite/secrets.yml") as f:
            secrets = yaml.safe_load(f)

        self.username = secrets["satellite"]["username"]
        self.token = secrets["satellite"]["token"]
        self.ssl_verify = False  # "/home/jr4238/satellite/katello-ca.crt"

        self.url = f"https://{site_name}/api/v2/hosts/{host_fqdn}"

        # self.session = requests.Session()
        # self.session.auth = (self.username, self.token)

        self.headers = {
            # "login": self.username,
            # "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Foreman-Api-Version": "2",
        }
        self.ssl_context = ssl.create_default_context(
            cafile="/home/jr4238/satellite/katello-ca.crt"
        )

    async def get_status(self):
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.token)
        ) as session:
            print(self.url + "/power")
            async with session.get(
                self.url + "/power", ssl=self.ssl_context, headers=self.headers
            ) as response:
                return await response.json()


class SatelliteAdapter(SiteAdapter):
    def __init__(self, host_fqdn: str, site_name: str):
        self._host_fqdn = host_fqdn
        self._site_name = site_name

        self.client = SatelliteClient(host_fqdn=self._host_fqdn)

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        print("Deploying resource...")

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        response = await self.client.get_status()
        status = response["state"]
        print(response)
        print(f"{self._host_fqdn} power state:", status)

        return AttributeDict()  # dummy for first

    async def stop_resource(self, resource_attributes: AttributeDict) -> None:
        print("Stopping resource...")

    async def terminate_resource(self, resource_attributes: AttributeDict) -> None:
        print("Terminating resource...")

    @contextmanager
    def handle_exceptions(self):
        print("kontext!")


if __name__ == "__main__":
    # Example usage
    adapter = SatelliteAdapter(machine_type="example_machine", site_name="example_site")
    print(
        f"Adapter created for machine type: {adapter.machine_type} on site: {adapter.site_name}"
    )

    adapter.resource_status(AttributeDict({"id": "12345"}))
