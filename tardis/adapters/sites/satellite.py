import asyncio
import logging
import ssl
from contextlib import contextmanager
from functools import partial
from typing import Optional

import aiohttp

from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import ResourceStatus, SiteAdapter
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.staticmapping import StaticMapping

logger = logging.getLogger("cobald.runtime.tardis.interfaces.site")


class SatelliteClient:
    """
    Async helper for interacting with Satellite instance.
    """

    def __init__(
        self,
        host: str,
        username: str,
        secret: str,
        ca_file: str,
        machine_pool: list[str],
        max_age: int,
        proxy: Optional[str] = None,
    ) -> None:

        self._base_url = f"https://{host}/api/v2/hosts"
        self.ssl_context = ssl.create_default_context(cafile=ca_file)
        self.auth = aiohttp.BasicAuth(username, secret)
        self.headers = {
            "Accept": "application/json",
            "Foreman-Api-Version": "2",
        }

        self.machine_pool = machine_pool

        self.max_age = max_age * 60
        self.cached_status_coroutines = {}
        self.proxy = proxy if proxy else None

    def _host_url(self, remote_resource_uuid: Optional[str] = None) -> str:
        if not remote_resource_uuid:
            return f"{self._base_url}/"
        resource = remote_resource_uuid.strip("/")
        return f"{self._base_url}/{resource}"

    async def _request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        **kwargs,
    ):
        async with session.request(
            method,
            url,
            ssl=self.ssl_context,
            headers=self.headers,
            proxy=self.proxy,
            **kwargs,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_status(self, remote_resource_uuid: str) -> dict:
        """
        Return host data together with custom parameters and power details.

        :param remote_resource_uuid: Satellite identifier of the host.
        :type remote_resource_uuid: str
        :return: Satellite host data enriched with parameters and power state.
        :rtype: dict
        """
        async with aiohttp.ClientSession(auth=self.auth) as session:
            host_url = self._host_url(remote_resource_uuid)
            main_task = self._request(session, "GET", host_url)
            params_task = self._request(session, "GET", f"{host_url}/parameters")
            power_task = self._request(session, "GET", f"{host_url}/power")
            main_response, param_response, power_response = await asyncio.gather(
                main_task, params_task, power_task
            )

        # Flatten custom parameters for simpler lookups in later calls.
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
        """
        Set the power state of a host and update its cached status.

        :param state: Desired power state as understood by the Satellite API ["on"|"off"].
        :type state: str
        :param remote_resource_uuid: Satellite identifier of the host.
        :type remote_resource_uuid: str
        :return: Raw response from the Satellite power endpoint.
        :rtype: dict
        """

        if state not in ("on", "off"):
            raise ValueError(f"Invalid power state {state}")

        async with aiohttp.ClientSession(auth=self.auth) as session:
            logger.info(f"Set power {state} for {remote_resource_uuid}")
            power_action_result = await self._request(
                session,
                "PUT",
                f"{self._host_url(remote_resource_uuid)}/power",
                json={"power_action": state},
            )
        return power_action_result

    async def set_satellite_parameter(
        self, remote_resource_uuid: str, parameter: str, value: str
    ) -> None:
        """
        Create or update a Satellite host parameter using lower-case string values only and
        updates its cached status.

        :param remote_resource_uuid: Satellite identifier of the host.
        :type remote_resource_uuid: str
        :param parameter: Name of the parameter to update.
        :type parameter: str
        :param value: New parameter value.
        :type value: str
        """
        value = str(value).lower()
        status_response = await self.get_status(remote_resource_uuid)
        parameter_id = status_response.get("parameters", {}).get(f"{parameter}_id")

        async with aiohttp.ClientSession(auth=self.auth) as session:
            if parameter_id is not None:
                _ = await self._request(
                    session,
                    "PUT",
                    f"{self._host_url(remote_resource_uuid)}/parameters/{parameter_id}",
                    json={"value": value},
                )
                logger.info(
                    f"Updated satellite parameter {parameter} to {value} for {remote_resource_uuid}"
                )
            else:
                _ = await self._request(
                    session,
                    "POST",
                    f"{self._host_url(remote_resource_uuid)}/parameters",
                    json={"name": parameter, "value": value},
                )
                logger.info(
                    f"Created satellite parameter {parameter} with value {value} for {remote_resource_uuid}"
                )
        await self.get_status(remote_resource_uuid)


class SatelliteAdapter(SiteAdapter):
    """
    Translate Satellite host lifecycle operations to the SiteAdapter API.
    """

    _next_host_lock = asyncio.Lock()

    def __init__(self, machine_type: str, site_name: str):
        self._machine_type = machine_type
        self._site_name = site_name

        self.client = SatelliteClient(
            host=self.configuration.host,
            username=self.configuration.username,
            secret=self.configuration.secret,
            ca_file=self.configuration.ca_file,
            machine_pool=self.configuration.machine_pool,
            max_age=self.configuration.max_age,
            proxy=self.configuration.proxy,
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
        """
        Allocate an available host and ensure it is powered on.

        :param resource_attributes: Attributes describing the drone to deploy.
        :type resource_attributes: AttributeDict
        :return: Normalised response containing at least the remote UUID.
        :rtype: AttributeDict
        """
        remote_resource_uuid = await self.get_next_host()
        await self.client.set_power(
            state="on", remote_resource_uuid=remote_resource_uuid
        )

        # codeql[py/incorrect-call-arguments]
        return self.handle_response({"remote_resource_uuid": remote_resource_uuid})

    async def get_next_host(self) -> str:
        """
        Select the next free host by checking reservation and power state.

        :return: Identifier of a reserved and powered-off host ready for use.
        :raises TardisResourceStatusUpdateFailed: If no free host is available.
        """

        async with SatelliteAdapter._next_host_lock:
            for host in self.configuration.machine_pool:
                resource_status = await self.client.get_status(host)
                parameters = resource_status.get("parameters", {})
                reservation_state = parameters.get("tardis_reservation_state", "free")
                is_free = reservation_state == "free"

                power_state = resource_status.get("power", {}).get("state")
                is_powered_off = power_state == "off"

                if is_free and is_powered_off:
                    await self.client.set_satellite_parameter(
                        host, "tardis_reservation_state", "booting"
                    )
                    logger.info(f"Allocated satellite host {host}")
                    return host

        logger.info("No free host found, skipping deployment")
        raise TardisResourceStatusUpdateFailed("no free host found")

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        """
        Query Satellite information and translate to ResourceStatus. If the drone
        is marked as terminating, free the host to be used in the next heartbeat interval.

        :param resource_attributes: Attributes describing the tracked drone.
        :type resource_attributes: AttributeDict
        :return: Normalised response containing the translated resource status.
        :rtype: AttributeDict
        """
        response = await self.client.get_status(
            resource_attributes.remote_resource_uuid
        )

        power_state = response.get("power", {}).get("state")
        reservation_state = response.get("parameters", {}).get(
            "tardis_reservation_state"
        )

        status = self._resolve_status(power_state, reservation_state)
        if status is ResourceStatus.Deleted:
            await self.client.set_satellite_parameter(
                resource_attributes.remote_resource_uuid,
                "tardis_reservation_state",
                "free",
            )
        elif status is ResourceStatus.Running and reservation_state == "booting":
            await self.client.set_satellite_parameter(
                resource_attributes.remote_resource_uuid,
                "tardis_reservation_state",
                "active",
            )
        return self.handle_response(
            response,
            resource_status=status,
            remote_resource_uuid=resource_attributes.remote_resource_uuid,
        )

    async def stop_resource(self, resource_attributes: AttributeDict) -> AttributeDict:
        """
        Request a power-off for the resource.

        :param resource_attributes: Attributes describing the drone to stop.
        :type resource_attributes: AttributeDict
        :return: Normalised response including the resulting resource status.
        :rtype: AttributeDict
        """
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
        """
        Flag a host as terminating so a later status check frees it.

        :param resource_attributes: Attributes describing the drone to retire.
        :type resource_attributes: AttributeDict
        """
        await self.client.set_satellite_parameter(
            resource_attributes.remote_resource_uuid,
            "tardis_reservation_state",
            "terminating",
        )

    @contextmanager
    def handle_exceptions(self):
        """
        Propagate Satellite-specific status failures unchanged. Especially if
        no free host is available during deployment.

        :return: Context manager yielding control to the caller.
        :rtype: contextmanager
        """
        try:
            yield
        except TardisResourceStatusUpdateFailed:
            raise

    def _resolve_status(
        self, power_state: Optional[str], reservation_state: Optional[str]
    ) -> ResourceStatus:
        """
        Translate raw Satellite flags into the canonical ``ResourceStatus``.

        :param power_state: Reported power state of the host.
        :type power_state: str or None
        :param reservation_state: Reservation flag managed via host parameters.
        :type reservation_state: str or None
        :return: Resource status understood by TARDIS.
        :rtype: ResourceStatus
        """
        if reservation_state == "booting":
            # booting hosts report as running once their power state flips to on
            if power_state == "on":
                return ResourceStatus.Running
            return ResourceStatus.Booting

        if power_state == "on":
            return ResourceStatus.Running

        if power_state == "off":
            # if resource is offline its either in stopping/terminating
            # phase or (still) booting
            if reservation_state == "terminating":
                return ResourceStatus.Deleted
            if reservation_state == "active":
                return ResourceStatus.Stopped

        # each other state should be treated as error
        return ResourceStatus.Error
