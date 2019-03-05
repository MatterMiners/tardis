from ..interfaces.executor import Executor
from ..utilities.attributedict import AttributeDict

import asyncio


class ShellExecutor(Executor):
    async def run_command(self, command):
        sub_process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await sub_process.communicate()

        return AttributeDict(stdout=stdout.decode().strip(), stderr=stderr.decode().strip(),
                             exit_code=sub_process.returncode)
