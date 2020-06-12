from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.utils import async_run_command
from tardis.utilities.utils import htcondor_cmd_option_formatter
from tardis.utilities.utils import csv_parser
from tardis.utilities.utils import slurm_cmd_option_formatter
from tardis.exceptions.executorexceptions import CommandExecutionFailure

from ..utilities.utilities import run_async

from unittest import TestCase


class TestAsyncRunCommand(TestCase):
    def test_async_run_command(self):
        run_async(async_run_command, "exit 0")
        run_async(async_run_command, "exit 255")

        with self.assertRaises(CommandExecutionFailure):
            run_async(async_run_command, "exit 1")

        self.assertEqual(run_async(async_run_command, 'echo "Test"'), "Test")


class TestHTCondorCMDOptionFormatter(TestCase):
    def test_htcondor_cmd_option_formatter(self):
        options = AttributeDict(pool="my-htcondor.local", test=None)
        option_string = htcondor_cmd_option_formatter(options)

        self.assertEqual(option_string, "-pool my-htcondor.local -test")

        options = AttributeDict()
        option_string = htcondor_cmd_option_formatter(options)

        self.assertEqual(option_string, "")


class TestCSVParser(TestCase):
    def test_csv_parser(self):
        htcondor_input = "\n".join(
            [
                "exoscale-26d361290f\tUnclaimed\tIdle\t0.125\t0.125",
                "test_replace\tOwner\tIdle\tundefined\tundefined",
            ]
        )

        parsed_rows = csv_parser(
            input_csv=htcondor_input,
            fieldnames=("Machine", "State", "Activity", "Test1", "Test2"),
            replacements=dict(undefined=None),
        )

        self.assertEqual(
            next(parsed_rows),
            dict(
                Machine="exoscale-26d361290f",
                State="Unclaimed",
                Activity="Idle",
                Test1="0.125",
                Test2="0.125",
            ),
        )

        self.assertEqual(
            next(parsed_rows),
            dict(
                Machine="test_replace",
                State="Owner",
                Activity="Idle",
                Test1=None,
                Test2=None,
            ),
        )


class TestSlurmCMDOptionFormatter(TestCase):
    def test_slurm_cmd_option_formatter(self):
        options = AttributeDict()
        option_string = slurm_cmd_option_formatter(options)

        self.assertEqual(option_string, "")

        options = AttributeDict(short=AttributeDict(foo="bar", test=None))
        option_string = slurm_cmd_option_formatter(options)

        self.assertEqual(option_string, "-foo bar -test")

        options = AttributeDict(long=AttributeDict(foo="bar", test=None))
        option_string = slurm_cmd_option_formatter(options)

        self.assertEqual(option_string, "--foo=bar --test")

        options = AttributeDict(
            short=AttributeDict(foo="bar", test=None),
            long=AttributeDict(foo_long="bar_long", test_long=None),
        )
        option_string = slurm_cmd_option_formatter(options)

        self.assertEqual(
            option_string, "-foo bar -test --foo_long=bar_long --test_long"
        )
