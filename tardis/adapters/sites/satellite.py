from tardis.interfaces.siteadapter import SiteAdapter
from tardis.utilities.attributedict import AttributeDict

from contextlib import contextmanager

from simple_rest_client.exceptions import AuthError
from simple_rest_client.exceptions import ClientError
from tardis.exceptions.tardisexceptions import TardisAuthError
from tardis.exceptions.tardisexceptions import TardisDroneCrashed
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from aiohttp import ClientConnectionError
from aiohttp import ContentTypeError
from tardis.utilities.staticmapping import StaticMapping
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.interfaces.siteadapter import SiteAdapter
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.staticmapping import StaticMapping

from functools import partial

import requests
import logging
import yaml
import aiohttp
import ssl


logger = logging.getLogger("cobald.runtime.tardis.interfaces.site")


def check_for_parameter(response, parameter):
    return next((p for p in response["parameters"] if p["name"] == parameter), None)


class SatelliteClient:
    # todo:
    # 2 min caching (see other adapters)
    def __init__(self, machine_type: str, site_name: str = "satellite.scc.kit.edu"):

        self._machine_type = machine_type
        self._site_name = site_name

        with open("/home/jr4238/satellite/secrets.yml") as f:
            secrets = yaml.safe_load(f)
        self.username = secrets["satellite"]["username"]
        self.token = secrets["satellite"]["token"]
        self.ssl_verify = False  # "/home/jr4238/satellite/katello-ca.crt"
        self.headers = {
            "Accept": "application/json",
            "Foreman-Api-Version": "2",
        }
        self.ssl_context = ssl.create_default_context(
            cafile="/home/jr4238/satellite/katello-ca.crt"
        )
        self.auth = aiohttp.BasicAuth(self.username, self.token)

    def url(self, remote_resource_uuid: str):
        return f"https://{self._site_name}/api/v2/hosts/{remote_resource_uuid}"

    async def get_status(self, remote_resource_uuid: str = None):

        url = self.url(remote_resource_uuid)

        async with aiohttp.ClientSession(auth=self.auth) as session:
            async with session.get(
                url,
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
        action_map = {"on": "on", "off": "off", "start": "on", "stop": "off"}
        if state not in action_map:
            raise ValueError("Use 'on'/'off' (or 'start'/'stop').")
        async with aiohttp.ClientSession(auth=self.auth) as session:
            async with session.put(
                self.url(remote_resource_uuid) + "/power",
                json={"power_action": state},
                ssl=self.ssl_context,
                headers=self.headers,
            ) as response:
                return await response.json()

    async def change_resource_reservation(
        self, remote_resource_uuid: str, reserved: bool
    ):
        async with aiohttp.ClientSession(auth=self.auth) as session:
            async with session.post(
                self.url(remote_resource_uuid) + "/parameters",
                json={"host": {"reserved": reserved}},
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
        self._machine_type = machine_type
        self._site_name = site_name
        self.client = SatelliteClient(machine_type=self._machine_type)

        key_translator = StaticMapping(
            remote_resource_uuid="remote_resource_uuid",
            resource_status="resource_status",
        )  # , drone_uuid="name")

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
        # specs = dict(name=resource_attributes.drone_uuid)
        # specs.update(self.machine_type_configuration)

        remote_resource_uuid = await self.client.get_next_uuid()
        await self.client.set_power("on", remote_resource_uuid)

        response = {}

        # response["resource_status"] = ResourceStatus.Booting
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
        print("--------------------           stopping placeholder :)")
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
        print("--------------------           terminating placeholder :)")
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
