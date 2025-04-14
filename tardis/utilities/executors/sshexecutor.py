from typing import Optional
from ...configuration.utilities import enable_yaml_load
from ...exceptions.tardisexceptions import TardisAuthError
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...interfaces.executor import Executor
from ..attributedict import AttributeDict
from cobald.daemon.plugins import yaml_tag

import asyncio
import asyncssh
import logging
import pyotp
from asyncssh.auth import KbdIntPrompts, KbdIntResponse
from asyncssh.client import SSHClient
from asyncssh.misc import MaybeAwait

from asyncstdlib import (
    ExitStack as AsyncExitStack,
    contextmanager as asynccontextmanager,
)

from functools import partial


logger = logging.getLogger("cobald.runtime.tardis.utilities.executors.sshexecutor")


async def probe_max_session(connection: asyncssh.SSHClientConnection):
    """
    Probe the sshd `MaxSessions`, i.e. the multiplexing limit per connection
    """
    sessions = 0
    # It does not actually matter what kind of session we open here, but:
    # - it should stay open without a separate task to manage it
    # - it should reliably and promptly clean up when done probing
    # `create_process` is a bit heavy but does all that.
    async with AsyncExitStack() as aes:
        try:
            while True:
                await aes.enter_context(await connection.create_process())
                sessions += 1
        except asyncssh.ChannelOpenError:
            pass
    return sessions


class MFASSHClient(SSHClient):
    def __init__(self, *args, mfa_config, **kwargs):
        super().__init__(*args, **kwargs)
        self._mfa_responses = {}
        for entry in mfa_config:
            self._mfa_responses[entry["prompt"].strip()] = pyotp.TOTP(entry["totp"])

    async def kbdint_auth_requested(self) -> MaybeAwait[Optional[str]]:
        """
        Keyboard-interactive authentication has been requested

        This method should return a string containing a comma-separated
        list of submethods that the server should use for
        keyboard-interactive authentication. An empty string can be
        returned to let the server pick the type of keyboard-interactive
        authentication to perform.
        """
        return ""

    async def kbdint_challenge_received(
        self, name: str, instructions: str, lang: str, prompts: KbdIntPrompts
    ) -> MaybeAwait[Optional[KbdIntResponse]]:
        """
        A keyboard-interactive auth challenge has been received

        This method is called when the server sends a keyboard-interactive
        authentication challenge.

        The return value should be a list of strings of the same length
        as the number of prompts provided if the challenge can be
        answered, or `None` to indicate that some other form of
        authentication should be attempted.
        """
        # prompts is of type Sequence[Tuple[str, bool]]
        try:
            return [self._mfa_responses[prompt[0].strip()].now() for prompt in prompts]
        except KeyError as ke:
            msg = f"Keyboard interactive authentication failed: Unexpected Prompt {ke}"
            logger.error(msg)
            raise TardisAuthError(msg) from ke


@enable_yaml_load("!SSHExecutor")
@yaml_tag(eager=True)
class SSHExecutor(Executor):
    def __init__(self, **parameters):
        self._parameters = parameters
        # enable Multi-factor Authentication if required
        if mfa_config := self._parameters.pop("mfa_config", None):
            self._parameters["client_factory"] = partial(
                MFASSHClient, mfa_config=mfa_config
            )
        # the current SSH connection and bound unless it must be (re-)established
        self._ssh_connection: (
            "tuple[asyncssh.SSHClientConnection, asyncio.Semaphore] | None"
        ) = None
        self._lock = None

    async def _establish_connection(self):
        for retry in range(1, 10):
            try:
                return await asyncssh.connect(**self._parameters)
            except (
                ConnectionResetError,
                asyncssh.DisconnectError,
                asyncssh.ConnectionLost,
                BrokenPipeError,
            ):
                await asyncio.sleep(retry * 10)
        return await asyncssh.connect(**self._parameters)

    def _handle_broken_ssh_connection(
        self,
        ssh_connection: asyncssh.SSHClientConnection,
        command: str,
        chained_exception: "Exception | None" = None,
    ):
        # clear broken connection to get it replaced
        # by a new connection during next command
        if (
            self._ssh_connection is not None
            and ssh_connection is self._ssh_connection[0]
        ):
            self._ssh_connection = None
        raise CommandExecutionFailure(
            message=(f"Could not run command {command} due to a connection loss!"),
            exit_code=255,
            stdout="",
            stderr="SSH connection lost",
        ) from chained_exception

    @property
    @asynccontextmanager
    async def bounded_connection(self):
        """
        Get the current connection with a single reserved session slot

        This is a context manager that guards the current
        :py:class:`~asyncssh.SSHClientConnection`
        so that only `MaxSessions` commands run at once.
        """
        if self._ssh_connection is None:
            async with self.lock:
                # check that connection has not been initialized in a different task
                while self._ssh_connection is None:
                    connection = await self._establish_connection()
                    max_session = await probe_max_session(connection)
                    self._ssh_connection = (
                        connection,
                        asyncio.Semaphore(value=max_session),
                    )
        assert self._ssh_connection is not None
        session, bound = self._ssh_connection
        async with bound:
            yield session

    @property
    def lock(self):
        """Lock protecting the connection"""
        # Create lock once tardis event loop is running.
        # To avoid got Future <Future pending> attached to a different loop exception
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def run_command(self, command, stdin_input=None):
        async with self.bounded_connection as ssh_connection:
            try:
                response = await ssh_connection.run(
                    command, check=True, input=stdin_input
                )
            except asyncssh.ProcessError as pe:
                raise CommandExecutionFailure(
                    message=f"Run command {command} via SSHExecutor failed",
                    exit_code=pe.exit_status,
                    stdin=stdin_input,
                    stdout=pe.stdout,
                    stderr=pe.stderr,
                ) from pe
            except asyncssh.ChannelOpenError as coe:
                self._handle_broken_ssh_connection(
                    ssh_connection, command, chained_exception=coe
                )
            else:
                # In case asyncssh loses the connection while running a command, the
                # connection loss seems to be silently ignored, however the
                # exit_status is None in that case.
                if response.exit_status is None:
                    self._handle_broken_ssh_connection(ssh_connection, command)
                return AttributeDict(
                    stdout=response.stdout,
                    stderr=response.stderr,
                    exit_code=response.exit_status,
                )


@enable_yaml_load("!DupingSSHExecutor")
@yaml_tag(eager=True)
class DupingSSHExecutor(SSHExecutor):
    def __init__(self, *, wrapper="/bin/bash", **parameters):
        self._wrapper_script = wrapper
        super().__init__(**parameters)

    async def run_command(self, command, stdin_input=None):
        stdin_input = f"{command}\n{stdin_input}\n" if stdin_input else f"{command}\n"
        return await super().run_command(self._wrapper_script, stdin_input=stdin_input)
