from ...configuration.utilities import enable_yaml_load
from ...exceptions.executorexceptions import CommandExecutionFailure
from asyncssh.misc import DisconnectError
from ...interfaces.executor import Executor
from ..attributedict import AttributeDict

import asyncssh


@enable_yaml_load('!SSHExecutor')
class SSHExecutor(Executor):
    def __init__(self, **parameters):
        self._parameters = parameters

    async def run_command(self, command, stdin_input=None):
        async with asyncssh.connect(**self._parameters) as conn:
            try:
                response = await conn.run(command, check=True)
            except asyncssh.ProcessError as pe:
                raise CommandExecutionFailure(message=f"Run command {command} via SSHExecutor failed",

                                              exit_code=pe.exit_status, stdout=pe.stdout, stderr=pe.stderr) from pe
            except (ConnectionResetError, DisconnectError) as ce:
                raise CommandExecutionFailure(message=f"Could not run command {command} due to SSH failure: {ce}",
                                              exit_code=255, stdout="", stderr="SSH failure") from ce
            else:
                return AttributeDict(stdout=response.stdout, stderr=response.stderr, exit_code=response.exit_status)
