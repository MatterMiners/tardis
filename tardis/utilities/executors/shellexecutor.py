from ...configuration.utilities import enable_yaml_load
from ...exceptions.executorexceptions import CommandExecutionFailure
from ...interfaces.executor import Executor
from ..attributedict import AttributeDict

import asyncio


@enable_yaml_load("!ShellExecutor")
class ShellExecutor(Executor):
    def __init__(self, *args, **kwargs):
        pass

    async def run_command(self, command):
        sub_process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await sub_process.communicate()
        exit_code = sub_process.returncode

        if exit_code:
            raise CommandExecutionFailure(message=f"Run command {command} via ShellExecutor failed",
                                          exit_code=exit_code, stdout=stdout, stderr=stderr)

        return AttributeDict(stdout=stdout.decode().strip(), stderr=stderr.decode().strip(),
                             exit_code=exit_code)
