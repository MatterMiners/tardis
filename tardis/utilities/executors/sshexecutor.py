from ...configuration.utilities import enable_yaml_load
from ...interfaces.executor import Executor
from ..attributedict import AttributeDict

import asyncssh


@enable_yaml_load('!SSHExecutor')
class SSHExecutor(Executor):
    def __init__(self, **parameters):
        self._parameters = parameters

    async def run_command(self, command):
        async with asyncssh.connect(**self._parameters) as conn:
            response = await conn.run(command, check=True)
            return AttributeDict(stdout=response.stdout, stderr=response.stderr, exit_code=response.exit_status)
