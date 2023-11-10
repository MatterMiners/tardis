from typing import Optional
from ...configuration.utilities import enable_yaml_load
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...interfaces.executor import Executor
from ..attributedict import AttributeDict

import asyncio
import asyncssh
from asyncstdlib import (
    ExitStack as AsyncExitStack,
    contextmanager as asynccontextmanager,
)


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


@enable_yaml_load("!SSHExecutor")
class SSHExecutor(Executor):
    def __init__(self, **parameters):
        self._parameters = parameters
        # the current SSH connection or None if it must be (re-)established
        self._ssh_connection: Optional[asyncssh.SSHClientConnection] = None
        # the bound on MaxSession running concurrently
        self._session_bound: Optional[asyncio.Semaphore] = None
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
                    self._ssh_connection = await self._establish_connection()
                    max_session = await probe_max_session(self._ssh_connection)
                    self._session_bound = asyncio.Semaphore(value=max_session)
        assert self._ssh_connection is not None
        assert self._session_bound is not None
        bound, session = self._session_bound, self._ssh_connection
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
                # clear broken connection to get it replaced
                # by a new connection during next command
                if ssh_connection is self._ssh_connection:
                    self._ssh_connection = None
                raise CommandExecutionFailure(
                    message=(
                        f"Could not run command {command} due to SSH failure: {coe}"
                    ),
                    exit_code=255,
                    stdout="",
                    stderr="SSH Broken Connection",
                ) from coe
            else:
                return AttributeDict(
                    stdout=response.stdout,
                    stderr=response.stderr,
                    exit_code=response.exit_status,
                )
