from .executors.shellexecutor import ShellExecutor
from ..exceptions.tardisexceptions import AsyncRunCommandFailure
from ..exceptions.executorexceptions import CommandExecutionFailure

from io import StringIO

import csv


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


def htcondor_csv_parser(htcondor_input, fieldnames, delimiter='\t', replacements=None):
    replacements = replacements or {}
    with StringIO(htcondor_input) as csv_input:
        cvs_reader = csv.DictReader(csv_input, fieldnames=fieldnames, delimiter=delimiter)
        for row in cvs_reader:
            yield {key: value if value not in replacements.keys() else replacements[value]
                   for key, value in row.items()}
