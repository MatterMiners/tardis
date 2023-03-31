import logging

from tardis.resources.dronestates import RequestState
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.utils import (
    convert_to,
    csv_parser,
    disable_logging,
    drone_environment_to_str,
    htcondor_cmd_option_formatter,
    load_states,
    submit_cmd_option_formatter,
)


from unittest import TestCase


class TestConvertTo(TestCase):
    def test_convert_to(self):
        for value, instance, converted_value in (
            (1, int, 1),
            ("1", int, 1),
            (1, float, 1),
            ("§$%", float, "§$%"),
        ):
            result = convert_to(value, instance, value)
            self.assertEqual(converted_value, result)


class TestDroneEnvironmentToStr(TestCase):
    def test_drone_environment_to_str(self):
        test_environment = {"Uuid": "test-abcfed", "Cores": 8, "Memory": 20.0}

        for drone_environment_to_str_kwargs, result in (
            (
                {
                    "seperator": ",",
                    "prefix": "TardisDrone",
                },
                "TardisDroneUuid=test-abcfed,TardisDroneCores=8,TardisDroneMemory=20.0",
            ),
            (
                {
                    "seperator": " ",
                    "prefix": "--",
                },
                "--Uuid=test-abcfed --Cores=8 --Memory=20.0",
            ),
            (
                {
                    "seperator": ",",
                    "prefix": "TardisDrone",
                    "customize_value": lambda x: convert_to(x, int, x),
                },
                "TardisDroneUuid=test-abcfed,TardisDroneCores=8,TardisDroneMemory=20",
            ),
            (
                {
                    "seperator": " ",
                    "prefix": "--",
                    "customize_key": str.lower,
                    "customize_value": lambda x: convert_to(x, int, x),
                },
                "--uuid=test-abcfed --cores=8 --memory=20",
            ),
        ):
            drone_environments_str = drone_environment_to_str(
                test_environment, **drone_environment_to_str_kwargs
            )
            self.assertEqual(
                drone_environments_str,
                result,
            )


class TestHTCondorCMDOptionFormatter(TestCase):
    def test_htcondor_cmd_option_formatter(self):
        options = AttributeDict(pool="my-htcondor.local", test=None)
        option_string = htcondor_cmd_option_formatter(options)

        self.assertEqual(option_string, "-pool my-htcondor.local -test")

        options = AttributeDict()
        option_string = htcondor_cmd_option_formatter(options)

        self.assertEqual(option_string, "")


class TestCSVParser(TestCase):
    def test_csv_parser_htcondor(self):
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

    def test_csv_parser_slurm(self):
        slurm_input = "\n".join(
            [
                "mixed  2/38/0/40  8000  10000  site-123  host-1    ",
                "idle   0/40/0/40     0  10000  site-124  host-2    ",
            ]
        )

        parsed_rows = csv_parser(
            input_csv=slurm_input,
            fieldnames=("State", "CPU", "AllocMem", "Memory", "Features", "NodeHost"),
            replacements=dict(undefined=None),
            delimiter=" ",
            skipinitialspace=True,
            skiptrailingspace=True,
        )

        self.assertEqual(
            next(parsed_rows),
            dict(
                State="mixed",
                CPU="2/38/0/40",
                AllocMem="8000",
                Memory="10000",
                Features="site-123",
                NodeHost="host-1",
            ),
        )

        self.assertEqual(
            next(parsed_rows),
            dict(
                State="idle",
                CPU="0/40/0/40",
                AllocMem="0",
                Memory="10000",
                Features="site-124",
                NodeHost="host-2",
            ),
        )


class TestDisableLogging(TestCase):
    def test_disable_logging(self):
        with self.assertLogs(level=logging.CRITICAL):
            with disable_logging(logging.DEBUG):
                logging.critical("Test")

        with self.assertRaises(AssertionError):  # check that nothing is logged
            with self.assertLogs(level=logging.DEBUG):
                with disable_logging(logging.DEBUG):
                    logging.debug("Test")


class TestStrToState(TestCase):
    def test_str_to_state(self):
        test = [{"state": "RequestState", "drone_uuid": "test-abc123"}]
        converted_test = load_states(test)
        self.assertTrue(converted_test[0]["state"], RequestState)
        self.assertEqual(converted_test[0]["drone_uuid"], "test-abc123")


class TestSlurmCMDOptionFormatter(TestCase):
    def test_submit_cmd_option_formatter(self):
        options = AttributeDict()
        option_string = submit_cmd_option_formatter(options)

        self.assertEqual(option_string, "")

        options = AttributeDict(short=AttributeDict(foo="bar", test=None))
        option_string = submit_cmd_option_formatter(options)

        self.assertEqual(option_string, "-foo bar -test")

        options = AttributeDict(long=AttributeDict(foo="bar", test=None))
        option_string = submit_cmd_option_formatter(options)

        self.assertEqual(option_string, "--foo=bar --test")

        options = AttributeDict(
            short=AttributeDict(foo="bar", test=None),
            long=AttributeDict(foo_long="bar_long", test_long=None),
        )
        option_string = submit_cmd_option_formatter(options)

        self.assertEqual(
            option_string, "-foo bar -test --foo_long=bar_long --test_long"
        )
