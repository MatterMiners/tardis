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


def csv_parser(
    input_csv: str,
    fieldnames: [List, Tuple],
    delimiter: str = "\t",
    replacements: dict = None,
    skipinitialspace: bool = False,
    skiptrailingspace: bool = False,
):
    """
    Parses CSV formatted input

    :param input_csv: CSV formatted input
    :type input_csv: str
    :param fieldnames: corresponding field names
    :type fieldnames: [List, Tuple]
    :param delimiter: delimiter between entries
    :type delimiter: str
    :param replacements: fields to be replaced
    :type replacements: dict
    :param skipinitialspace: ignore whitespace immediately following the delimiter
    :type skipinitialspace: bool
    :param skiptrailingspace: ignore whitespace at the end of each csv row
    :type skiptrailingspace: bool
    """
    if skiptrailingspace:
        input_csv = "\n".join((line.strip() for line in input_csv.splitlines()))

    replacements = replacements or {}
    with StringIO(input_csv) as csv_input:
        csv_reader = csv.DictReader(
            csv_input,
            fieldnames=fieldnames,
            delimiter=delimiter,
            skipinitialspace=skipinitialspace,
        )
        for row in csv_reader:
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
