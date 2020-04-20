from ...configuration.utilities import enable_yaml_load
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...interfaces.executor import Executor
from ..attributedict import AttributeDict

try:
    from contextlib import asynccontextmanager
except ImportError:
    from aiotools import async_ctx_manager as asynccontextmanager

import asyncssh
import asyncio


class SSHConnectionPool(object):
    _connection_pool = dict()
    _lock = None

    def __init__(self, connection_pool_size=5, **parameters):
        assert (
            "host" in parameters
        ), f"Host to connect to not found in parameters {parameters}"

        self._connection_pool_size = connection_pool_size
        self._host = parameters["host"]
        self._parameters = parameters

    @property
    def acquire_lock(self):
        # Create lock once tardis event loop is running.
        # To avoid got Future <Future pending> attached to a different loop exception
        if not self._lock:
            self._lock = asyncio.Lock()
        return self._lock

    async def establish_connection(self):
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

    async def _init_connection_pool(self):
        async with self.acquire_lock:
            # check that connection pool has not yet been initialize in a different task
            if self._host not in self._connection_pool:
                self._connection_pool[self._host] = asyncio.Queue()
                while (
                    self._connection_pool[self._host].qsize()
                    < self._connection_pool_size
                ):
                    await self._connection_pool[self._host].put(
                        await self.establish_connection()
                    )

    @asynccontextmanager
    async def get_connection(self):
        if self._host not in self._connection_pool:
            await self._init_connection_pool()

        active_connection = await self._connection_pool[self._host].get()

        try:
            yield active_connection
        except asyncssh.ChannelOpenError as coe:
            # Broken connection so replace active_connection by a new connection
            active_connection = await self.establish_connection()
            raise CommandExecutionFailure(
                message=f"Could not establish a channel due to SSH failure: {coe}",
                exit_code=255,
                stdout="",
                stderr="SSH failure",
            ) from coe
        finally:
            await self._connection_pool[self._host].put(active_connection)


@enable_yaml_load("!SSHExecutor")
class SSHExecutor(Executor):
    def __init__(self, **parameters):
        self._parameters = parameters
        self._ssh_connection_pool = SSHConnectionPool(**parameters)

    async def run_command(self, command, stdin_input=None):
        async with self._ssh_connection_pool.get_connection() as conn:
            try:
                response = await conn.run(
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
            else:
                return AttributeDict(
                    stdout=response.stdout,
                    stderr=response.stderr,
                    exit_code=response.exit_status,
                )
