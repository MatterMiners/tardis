import asyncio
import logging
import ssl
from contextlib import contextmanager
from functools import partial
from typing import Optional

import aiohttp

from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import ResourceStatus, SiteAdapter
from tardis.plugins.sqliteregistry import SqliteRegistry
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
        domain: str,
        proxy: Optional[str] = None,
    ) -> None:

        self.domain = domain
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
        fqdn = remote_resource_uuid + self.domain
        return f"{self._base_url}/{fqdn}"

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
        Return host data together with power details.

        :param remote_resource_uuid: Satellite identifier of the host.
        :return: Satellite host data enriched with power state.
        """
        async with aiohttp.ClientSession(auth=self.auth) as session:
            host_url = self._host_url(remote_resource_uuid)
            main_task = self._request(session, "GET", host_url)
            power_task = self._request(session, "GET", f"{host_url}/power")
            main_response, power_response = await asyncio.gather(main_task, power_task)

        main_response["power"] = power_response
        return main_response

    async def set_power(self, state: str, remote_resource_uuid: str) -> dict:
        """
        Set the power state of a host and update its cached status.

        :param state: Desired power state as understood by the
        Satellite API ["on"|"off"].
        :param remote_resource_uuid: Satellite identifier of the host.
        :return: Raw response from the Satellite power endpoint.
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


class SatelliteAdapter(SiteAdapter):
    """
    Translate Satellite host lifecycle operations to the SiteAdapter API.
    """

    _next_host_lock = asyncio.Lock()

    def __init__(self, machine_type: str, site_name: str):
        self._machine_type = machine_type
        self._site_name = site_name

        try:
            self.registry = SqliteRegistry()
        except AttributeError as ae:
            raise AttributeError(
                "SatelliteAdapter requires the SqliteRegistry plugin "
                "(Plugins.SqliteRegistry) to be configured, since it is used "
                "as the drone database to claim and free hosts."
            ) from ae

        self.client = SatelliteClient(
            host=self.configuration.host,
            username=self.configuration.username,
            secret=self.configuration.secret,
            ca_file=self.configuration.ca_file,
            machine_pool=self.configuration.machine_pool,
            max_age=self.configuration.max_age,
            domain=self.configuration.domain,
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
        :return: Normalised response containing at least the remote UUID.
        """
        remote_resource_uuid = await self.get_next_host(resource_attributes)
        await self.client.set_power(
            state="on", remote_resource_uuid=remote_resource_uuid
        )

        # codeql[py/incorrect-call-arguments]
        return self.handle_response({"remote_resource_uuid": remote_resource_uuid})

    async def get_next_host(self, resource_attributes: AttributeDict) -> str:
        """
        Select the next free host and atomically claim it in the drone
        database to avoid double allocation. Double claiming is prevented in two stages:
        first, `occupied` and `SatelliteAdapter._next_host_lock` ensure that no two
        coroutines can claim the same host at the same time. Second,
        `registry.set_remote_resource_uuid` will return False if the host has already
        been claimed by another drone.

        :param resource_attributes: Attributes of the drone claiming a host.
        :return: Identifier of a claimed and powered-off host ready for use.
        :raises TardisResourceStatusUpdateFailed: If no free host is available.
        """

        async with SatelliteAdapter._next_host_lock:
            occupied = {
                row["remote_resource_uuid"]
                for row in await self.registry.async_get_resources(
                    self.site_name, self.machine_type
                )
                if row["remote_resource_uuid"]
            }

            for host in self.configuration.machine_pool:
                if host in occupied:
                    continue

                resource_status = await self.client.get_status(host)
                power_state = resource_status.get("power", {}).get("state")
                if power_state != "off":
                    continue

                claimed = await self.registry.set_remote_resource_uuid(
                    resource_attributes.drone_uuid, host, self.site_name
                )
                if not claimed:
                    continue

                logger.info(f"Allocated satellite host {host}")
                return host

        logger.info("No free host found, skipping deployment")
        raise TardisResourceStatusUpdateFailed("no free host found")

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        """
        Query Satellite information and translate to ResourceStatus.

        Tolerates ambiguous ``power`` states (e.g. ``na``) for up to
        ``max_ambiguous_polls`` polls, then initializes stopping.

        :param resource_attributes: Attributes describing the tracked drone.
        :return: Normalised response containing the translated resource status.
        """
        response = await self.client.get_status(
            resource_attributes.remote_resource_uuid
        )

        power = response.get("power", {})
        power_state = power.get("state")
        terminating = resource_attributes.get("satellite_terminating", False)
        previous_status = resource_attributes.get("resource_status")

        if power_state in ("on", "off") or terminating:
            resource_attributes["satellite_ambiguous_polls"] = 0
        else:
            ambiguous_polls = (
                resource_attributes.get("satellite_ambiguous_polls", 0) + 1
            )
            resource_attributes["satellite_ambiguous_polls"] = ambiguous_polls

            max_ambiguous_polls = self.configuration.get("max_ambiguous_polls", 3)
            if ambiguous_polls > max_ambiguous_polls:
                logger.error(
                    "%s: power state ambiguous (%r, %s) for %d consecutive "
                    "polls; forcing power off",
                    resource_attributes.remote_resource_uuid,
                    power_state,
                    power.get("statusText"),
                    ambiguous_polls,
                )
                return await self.stop_resource(resource_attributes)

        status = self._resolve_status(power_state, terminating, previous_status)
        return self.handle_response(
            response,
            resource_status=status,
            remote_resource_uuid=resource_attributes.remote_resource_uuid,
        )

    async def stop_resource(self, resource_attributes: AttributeDict) -> AttributeDict:
        """
        Request a power-off for the resource.

        :param resource_attributes: Attributes describing the drone to stop.
        :return: Normalised response including the resulting resource status.
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
        Mark the drone as terminating locally so a later status check reports
        it as deleted.

        :param resource_attributes: Attributes describing the drone to retire.
        """
        resource_attributes["satellite_terminating"] = True

    @contextmanager
    def handle_exceptions(self):
        """
        Propagate Satellite-specific status failures unchanged. Especially if
        no free host is available during deployment.

        :return: Context manager yielding control to the caller.
        """
        try:
            yield
        except TardisResourceStatusUpdateFailed:
            raise

    def _resolve_status(
        self,
        power_state: Optional[str],
        terminating: bool,
        previous_status: Optional[ResourceStatus],
    ) -> ResourceStatus:
        """
        Translate the Satellite power state, combined with locally known
        drone state, into the canonical ``ResourceStatus``.

        An ambiguous ``power_state`` (neither ``"on"`` nor ``"off"``) carries
        forward ``previous_status`` instead of becoming ``Error``, falling
        back to ``Error`` only when there's no previous status to trust.

        :param power_state: Reported power state of the host.
        :param terminating: Whether ``terminate_resource`` has been called
        for this drone already.
        :param previous_status: The ``ResourceStatus`` last reported for this
        drone, carried forward on ``resource_attributes``.
        :return: Resource status understood by TARDIS.
        """
        if terminating:
            return ResourceStatus.Deleted
        if power_state == "on":
            return ResourceStatus.Running

        if power_state == "off":
            # if resource is offline its either in stopping/terminating
            # phase or (still) booting
            if previous_status == ResourceStatus.Booting:
                return ResourceStatus.Booting
            return ResourceStatus.Stopped

        if previous_status == ResourceStatus.Booting:
            return ResourceStatus.Booting
        if previous_status is not None:
            logger.warning(
                "Ambiguous power state %r, keeping previous status %s",
                power_state,
                previous_status,
            )
            return previous_status

        # no known previous status to fall back on
        return ResourceStatus.Error
