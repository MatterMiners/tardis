import logging
import aiohttp
import ssl

from functools import partial
from contextlib import contextmanager

from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.utilities.staticmapping import StaticMapping
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.interfaces.siteadapter import SiteAdapter
from tardis.interfaces.siteadapter import SiteAdapter
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.staticmapping import StaticMapping
from tardis.utilities.attributedict import AttributeDict

logger = logging.getLogger("cobald.runtime.tardis.interfaces.site")


class SatelliteClient:
    # todo:
    # 2 min caching (see other adapters)
    def __init__(
        self,
        site_name: str,
        username: str,
        token: str,
        ssl_cert: str,
    ):

        self._site_name = site_name

        self.headers = {
            "Accept": "application/json",
            "Foreman-Api-Version": "2",
        }
        self.ssl_context = ssl.create_default_context(cafile=ssl_cert)

        self.auth = aiohttp.BasicAuth(username, token)

    def url(self, remote_resource_uuid: str):
        return f"https://{self._site_name}/api/v2/hosts/{remote_resource_uuid}"

    async def get_status(self, remote_resource_uuid: str = None):
        async with aiohttp.ClientSession(auth=self.auth) as session:
            async with session.get(
                self.url(remote_resource_uuid),
                ssl=self.ssl_context,
                headers=self.headers,
            ) as response:
                main_response = await response.json()

            async with session.get(
                self.url(remote_resource_uuid) + "/parameters",
                ssl=self.ssl_context,
                headers=self.headers,
            ) as response:
                param_response = await response.json()

            async with session.get(
                self.url(remote_resource_uuid) + "/power",
                ssl=self.ssl_context,
                headers=self.headers,
            ) as response:
                power_response = await response.json()

        param_dict = {}
        for param in param_response["results"]:
            param_dict[param["name"]] = param["value"]
            param_dict[param["name"] + "_id"] = param["id"]
        main_response["parameters"] = param_dict
        main_response["power"] = power_response
        return main_response

    async def set_power(self, state: str, remote_resource_uuid: str = None):
        async with aiohttp.ClientSession(auth=self.auth) as session:
            async with session.put(
                self.url(remote_resource_uuid) + "/power",
                json={"power_action": state},
                ssl=self.ssl_context,
                headers=self.headers,
            ) as response:
                return await response.json()

    async def get_next_uuid(self):
        # get all data from satellite instance
        async with aiohttp.ClientSession(auth=self.auth) as session:
            async with session.get(
                self.url(""),
                ssl=self.ssl_context,
                headers=self.headers,
            ) as response:
                data = await response.json()

        # filter only the host names and set their  status to None

        # Zum scharf schalten fuer alle hosts :-)
        # resources = [hostinfo["name"] for hostinfo in data["results"]]
        resources = ["cloud-monit.gridka.de"]

        # grep the power status for each host
        for host in resources:
            resource_status = await self.get_status(host)

            reserved_status = resource_status["parameters"].get(
                "tardis_reserved", "false"
            )
            is_unreserved = reserved_status == "false"

            is_powered_off = resource_status["power"]["state"] == "off"

            if is_unreserved and is_powered_off:
                await self.set_satellite_parameter(host, "tardis_reserved", "true")

                print("==================== returning free host ====================")
                print("returning free host: ", host)
                print("=============================================================")
                return host

        raise TardisResourceStatusUpdateFailed("no free host found")

    async def set_satellite_parameter(
        self, remote_resource_uuid: str, parameter: str, value: str
    ):
        value = str(value).lower()

        # get params
        status_response = await self.get_status(remote_resource_uuid)

        async with aiohttp.ClientSession(auth=self.auth) as session:
            if parameter in status_response["parameters"]:
                async with session.put(
                    self.url(remote_resource_uuid)
                    + "/parameters/"
                    + str(status_response["parameters"][parameter + "_id"]),
                    json={"value": value},
                    ssl=self.ssl_context,
                    headers=self.headers,
                ) as response:
                    data = await response.json()
            else:
                # create new param
                async with session.post(
                    self.url(remote_resource_uuid) + "/parameters",
                    json={"name": parameter, "value": value},
                    ssl=self.ssl_context,
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                status_response = await self.get_status(remote_resource_uuid)


class SatelliteAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str):
        self._site_name = site_name
        self.client = SatelliteClient(
            site_name=self.configuration.site_name,
            username=self.configuration.username,
            token=self.configuration.token,
            ssl_cert=self.configuration.ssl_cert,
        )

        key_translator = StaticMapping(
            remote_resource_uuid="remote_resource_uuid",
            resource_status="resource_status",
        )

        translator_functions = StaticMapping(
            status=lambda x, translator=StaticMapping(): translator[x],
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=translator_functions,
        )

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:

        remote_resource_uuid = await self.client.get_next_uuid()
        await self.client.set_power("on", remote_resource_uuid)

        response = {}
        response["remote_resource_uuid"] = remote_resource_uuid

        return self.handle_response(response)

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        response = await self.client.get_status(
            resource_attributes.remote_resource_uuid
        )

        power_status = response["power"]["state"]
        reserved_status = response["parameters"]["tardis_reserved"]

        if power_status == "on":
            response["resource_status"] = ResourceStatus.Running
        elif power_status == "off" and reserved_status == "terminating":
            response["resource_status"] = ResourceStatus.Deleted
            await self.client.set_satellite_parameter(
                resource_attributes.remote_resource_uuid,
                "tardis_reserved",
                "false",
            )
        elif power_status == "off" and reserved_status == "true":
            response["resource_status"] = ResourceStatus.Stopped
        else:
            response["resource_status"] = ResourceStatus.Error
        return self.handle_response(response)

    async def stop_resource(self, resource_attributes: AttributeDict) -> None:
        response = await self.client.set_power(
            "off", resource_attributes.remote_resource_uuid
        )
        if "error" in response.keys():
            print("error in stopping resource: ", response)
            response["resource_status"] = ResourceStatus.Error
        else:
            response["resource_status"] = ResourceStatus.Stopped
        return self.handle_response(response)

    async def terminate_resource(self, resource_attributes: AttributeDict) -> None:
        await self.client.set_satellite_parameter(
            resource_attributes.remote_resource_uuid, "tardis_reserved", "terminating"
        )

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TardisResourceStatusUpdateFailed:
            raise


if __name__ == "__main__":
    # Example usage
    adapter = SatelliteAdapter(machine_type="example_machine", site_name="example_site")
    print(
        f"Adapter created for machine type: {adapter.machine_type} on site: {adapter.site_name}"
    )

    adapter.resource_status(AttributeDict({"id": "12345"}))
