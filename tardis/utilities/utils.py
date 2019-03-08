from tardis.utilities.executors.shellexecutor import ShellExecutor
from ..exceptions.tardisexceptions import AsyncRunCommandFailure


async def async_run_command(cmd, shell_executor=ShellExecutor()):
    response = await shell_executor.run_command(cmd)

    # Potentially due to a Python bug, if waitpid(0) is called somewhere else, the message
    # "WARNING:asyncio:Unknown child process pid 2960761, will report returncode 255 appears"
    # However the command succeeded

    if response.exit_code in (0, 255):
        return response.stdout

    raise AsyncRunCommandFailure(message=response.stdout, error_code=response.exit_code, error_message=response.stderr)
