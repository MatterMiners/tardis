from ...configuration.utilities import enable_yaml_load
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

        return AttributeDict(stdout=stdout.decode().strip(), stderr=stderr.decode().strip(),
                             exit_code=sub_process.returncode)
