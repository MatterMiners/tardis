from ..exceptions.tardisexceptions import AsyncRunCommandFailure

import asyncio


async def async_run_command(cmd, *args):
    sub_process = await asyncio.create_subprocess_exec(cmd, *args, stdout=asyncio.subprocess.PIPE,
                                                       stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await sub_process.communicate()

    # Potentially due to a Python bug, if waitpid(0) is called somewhere else, the message
    # "WARNING:asyncio:Unknown child process pid 2960761, will report returncode 255 appears"
    # However the command succeeded

    if sub_process.returncode in (0, 255):
        return stdout.decode().strip()

    raise AsyncRunCommandFailure(message=stdout, error_code=sub_process.returncode, error_message=stderr)
