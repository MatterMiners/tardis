from .executors.shellexecutor import ShellExecutor
from ..exceptions.tardisexceptions import AsyncRunCommandFailure
from ..exceptions.executorexceptions import CommandExecutionFailure


async def async_run_command(cmd, shell_executor=ShellExecutor()):
    try:
        response = await shell_executor.run_command(cmd)
    except CommandExecutionFailure as ef:
        # Potentially due to a Python bug, if waitpid(0) is called somewhere else, the message
        # "WARNING:asyncio:Unknown child process pid 2960761, will report returncode 255 appears"
        # However the command succeeded

        if ef.exit_code == 255:
            return ef.stdout
        raise AsyncRunCommandFailure(message=ef.stdout, error_code=ef.exit_code, error_message=ef.stderr) from ef
    else:
        return response.stdout
