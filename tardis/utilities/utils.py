from .attributedict import AttributeDict
from .executors.shellexecutor import ShellExecutor
from ..exceptions.executorexceptions import CommandExecutionFailure
from ..interfaces.executor import Executor

from io import StringIO
from typing import List, Tuple

import csv


async def async_run_command(
    cmd: str, shell_executor: Executor = ShellExecutor()
) -> str:
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


def cmd_option_formatter(options: AttributeDict, prefix: str, separator: str) -> str:
    options = (
        f"{prefix}{name}{separator}{value}" if value is not None else f"{prefix}{name}"
        for name, value in options.items()
    )

    return " ".join(options)


def htcondor_cmd_option_formatter(options: AttributeDict) -> str:
    return cmd_option_formatter(options, prefix="-", separator=" ")


def htcondor_csv_parser(
    htcondor_input: str,
    fieldnames: [List, Tuple],
    delimiter: str = "\t",
    replacements: dict = None,
):
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


def slurm_cmd_option_formatter(options: AttributeDict) -> str:
    option_prefix = dict(short="-", long="--")
    option_separator = dict(short=" ", long="=")

    option_string = ""

    for option_type in ("short", "long"):
        try:
            tmp_option_string = cmd_option_formatter(
                getattr(options, option_type),
                prefix=option_prefix[option_type],
                separator=option_separator[option_type],
            )
        except AttributeError:
            pass
        else:
            if option_string:  # add additional space between short and long options
                option_string += " "
            option_string += tmp_option_string

    return option_string
