from .executors.shellexecutor import ShellExecutor
from ..exceptions.executorexceptions import CommandExecutionFailure

from io import StringIO

import csv


async def async_run_command(cmd, shell_executor=ShellExecutor()):
    try:
        response = await shell_executor.run_command(cmd)
    except CommandExecutionFailure as ef:
        # Potentially due to a Python bug, if waitpid(0) is called somewhere else,
        # the message "WARNING:asyncio:Unknown child process pid 2960761,
        # will report returncode 255 appears"
        # However the command succeeded

        if ef.exit_code == 255:
            return ef.stdout
        raise
    else:
        return response.stdout


def htcondor_cmd_option_formatter(options):
    options = (
        f"-{name} {value}" if value is not None else f"-{name}"
        for name, value in options.items()
    )

    return " ".join(options)


def htcondor_csv_parser(htcondor_input, fieldnames, delimiter="\t", replacements=None):
    replacements = replacements or {}
    with StringIO(htcondor_input) as csv_input:
        cvs_reader = csv.DictReader(
            csv_input, fieldnames=fieldnames, delimiter=delimiter
        )
        for row in cvs_reader:
            yield {
                key: value if value not in replacements.keys() else replacements[value]
                for key, value in row.items()
            }


def slurm_cmd_option_formatter(options):
    """
    Formats name/value pais in the `options` dict as `--<name> value` suitable
    for passing to SLURM command line tools.

    :param options:  name/value pairs
    :type options: AttributeDict
    """
    options = (
        f"--{name} {value}" if value is not None else f"--{name}"
        for name, value in options.items()
    )

    return " ".join(options)


def slurm_csv_parser(slurm_input, fieldnames, delimiter=" ", replacements=None):
    """
    Parses the output of Slurm commands

    :param slurm_input: Slurm command response
    :type slurm_input: str
    :param fieldnames: corresponding field names
    :type fieldnames: str
    :param delimiter: delimiter between entries
    :type delimiter: char
    :param replacements: fields to be replaced
    :type replacements: str
    """
    # TODO: add replacements functionality to be consistent with htcondor parser
    #  replacements = replacements or {}
    with StringIO(slurm_input) as csv_input:
        cvs_reader = csv.DictReader(
            csv_input, fieldnames=fieldnames, delimiter=delimiter, skipinitialspace=True
        )
        for row in cvs_reader:
            yield {
                key: value
                #  if value not in replacements.keys()
                #  else replacements[value]
                for key, value in row.items()
            }
