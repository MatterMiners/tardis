import asyncio
import logging
import ssl
from contextlib import contextmanager
from functools import partial

import aiohttp

from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import ResourceStatus, SiteAdapter
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.staticmapping import StaticMapping

logger = logging.getLogger("cobald.runtime.tardis.interfaces.site")


class SatelliteClient:
    # todo:
    # 2 min caching (see other adapters)

    _API_PATH = "/api/v2/hosts"

    def __init__(
        self,
        site_name: str,
        username: str,
        token: str,
        ssl_cert: str,
    ) -> None:

        self._base_url = f"https://{site_name}{self._API_PATH}"
        self.headers = {
            "Accept": "application/json",
            "Foreman-Api-Version": "2",
        }
        self.ssl_context = ssl.create_default_context(cafile=ssl_cert)
        self.auth = aiohttp.BasicAuth(username, token)

    def _host_url(self, remote_resource_uuid: str = "") -> str:
        if remote_resource_uuid == "":
            return f"{self._base_url}/"
        resource = remote_resource_uuid.strip("/")
        return f"{self._base_url}/{resource}"

    async def _request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        *,
        expect_json: bool = True,
        **kwargs,
    ):
        async with session.request(
            method,
            url,
            ssl=self.ssl_context,
            headers=self.headers,
            **kwargs,
        ) as response:
            response.raise_for_status()
            if expect_json:
                return await response.json()
            return None

    async def get_status(self, remote_resource_uuid: str) -> dict:
        async with aiohttp.ClientSession(auth=self.auth) as session:
            host_url = self._host_url(remote_resource_uuid)
            main_task = self._request(session, "GET", host_url)
            params_task = self._request(session, "GET", f"{host_url}/parameters")
            power_task = self._request(session, "GET", f"{host_url}/power")
            main_response, param_response, power_response = await asyncio.gather(
                main_task, params_task, power_task
            )

        # collect custom parameters
        parameters = {}
        for param in param_response.get("results", []):
            name = param.get("name")
            if not name:
                continue
            if "value" in param:
                parameters[name] = param["value"]
            if "id" in param:
                parameters[f"{name}_id"] = param["id"]

        main_response["parameters"] = parameters
        main_response["power"] = power_response
        return main_response

    async def set_power(self, state: str, remote_resource_uuid: str) -> dict:
        async with aiohttp.ClientSession(auth=self.auth) as session:
            return await self._request(
                session,
                "PUT",
                f"{self._host_url(remote_resource_uuid)}/power",
                json={"power_action": state},
            )
        logger.info(f"Set power {state} for {remote_resource_uuid}")

    async def get_next_uuid(self) -> str:
        async with aiohttp.ClientSession(auth=self.auth) as session:
            data = await self._request(session, "GET", self._host_url())

        # Zum scharf schalten :)
        # resources = [
        #    host.get("name") for host in data.get("results", []) if host.get("name")
        # ]
        resources = ["cloud-monit.gridka.de"]

        for host in resources:
            resource_status = await self.get_status(host)
            parameters = resource_status.get("parameters", {})
            reserved_status = parameters.get("tardis_reserved", "false")
            is_unreserved = reserved_status == "false"

            power_state = resource_status.get("power", {}).get("state")
            is_powered_off = power_state == "off"

            if is_unreserved and is_powered_off:
                await self.set_satellite_parameter(host, "tardis_reserved", "true")
                logger.info(f"Allocated satellite host {host}")
                return host

        logger.info("No free host found, skipping deployment")
        raise TardisResourceStatusUpdateFailed("no free host found")

    async def set_satellite_parameter(
        self, remote_resource_uuid: str, parameter: str, value: str
    ) -> None:
        value = str(value).lower()
        status_response = await self.get_status(remote_resource_uuid)
        parameter_id = status_response.get("parameters", {}).get(f"{parameter}_id")

        async with aiohttp.ClientSession(auth=self.auth) as session:
            if parameter_id is not None:
                await self._request(
                    session,
                    "PUT",
                    f"{self._host_url(remote_resource_uuid)}/parameters/{parameter_id}",
                    json={"value": value},
                    expect_json=False,
                )
                logger.info(
                    f"Updated satellite parameter {parameter} to {value} for {remote_resource_uuid}"
                )
            else:
                await self._request(
                    session,
                    "POST",
                    f"{self._host_url(remote_resource_uuid)}/parameters",
                    json={"name": parameter, "value": value},
                    expect_json=False,
                )
                logger.info(
                    f"Created satellite parameter {parameter} with value {value} for {remote_resource_uuid}"
                )


class SatelliteAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str):
        self._machine_type = machine_type
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

        return self.handle_response({"remote_resource_uuid": remote_resource_uuid})

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        response = await self.client.get_status(
            resource_attributes.remote_resource_uuid
        )

        power_state = response.get("power", {}).get("state")
        reserved_state = response.get("parameters", {}).get("tardis_reserved")

        status = self._resolve_status(power_state, reserved_state)
        if status is ResourceStatus.Deleted:
            await self.client.set_satellite_parameter(
                resource_attributes.remote_resource_uuid,
                "tardis_reserved",
                "false",
            )
        return self.handle_response(
            response,
            resource_status=status,
            remote_resource_uuid=resource_attributes.remote_resource_uuid,
        )

    async def stop_resource(self, resource_attributes: AttributeDict) -> None:
        response = await self.client.set_power(
            "off", resource_attributes.remote_resource_uuid
        )
        has_error = "error" in response
        if has_error:
            logger.error(
                "Failed to stop satellite resource %s: %s",
                resource_attributes.remote_resource_uuid,
                response,
            )

        status = ResourceStatus.Error if has_error else ResourceStatus.Stopped
        return self.handle_response(
            response,
            resource_status=status,
            remote_resource_uuid=resource_attributes.remote_resource_uuid,
        )

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

    def _resolve_status(self, power_state: str, reserved_state: str) -> ResourceStatus:
        if power_state == "on":
            return ResourceStatus.Running

        if power_state == "off":
            if reserved_state == "terminating":
                return ResourceStatus.Deleted
            if reserved_state == "true":
                return ResourceStatus.Stopped

        return ResourceStatus.Error
