from ...configuration.utilities import enable_yaml_load
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...interfaces.executor import Executor
from ..attributedict import AttributeDict

import asyncio
import asyncssh


@enable_yaml_load("!SSHExecutor")
class SSHExecutor(Executor):
    def __init__(self, **parameters):
        self._parameters = parameters
        self._ssh_connection = None
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
    async def ssh_connection(self):
        if self._ssh_connection is None:
            async with self.lock:
                # check that connection has not yet been initialize in a different task
                while self._ssh_connection is None:
                    self._ssh_connection = await self._establish_connection()
        return self._ssh_connection

    @property
    def lock(self):
        # Create lock once tardis event loop is running.
        # To avoid got Future <Future pending> attached to a different loop exception
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def run_command(self, command, stdin_input=None):
        ssh_connection = await self.ssh_connection
        try:
            response = await ssh_connection.run(
                command, check=True, input=stdin_input and stdin_input.encode()
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
            # Broken connection will be replaced by a new connection during next call
            self._ssh_connection = None
            raise CommandExecutionFailure(
                message=f"Could not run command {command} due to SSH failure: {coe}",
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
