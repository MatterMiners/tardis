import logging

from tardis.resources.dronestates import RequestState
from tardis.utilities.attributedict import AttributeDict
from tardis.utilities.utils import (
    csv_parser,
    deep_update,
    disable_logging,
    htcondor_cmd_option_formatter,
    load_states,
    submit_cmd_option_formatter,
)


from unittest import TestCase


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


class TestDeepUpdate(TestCase):
    def test_deep_update_simple_dict(self):
        original_mapping = {"test": 123, "NoChange": 789}
        mapping_update = {"test": 456}
        updated_mapping = {"NoChange": 789, "test": 456}

        self.assertDictEqual(
            updated_mapping, deep_update(original_mapping, mapping_update)
        )

    def test_deep_update_nested_dict(self):
        original_mapping = {
            "test": {"test": 123},
            "NoChange1": 123,
            "NoChange2": {"Test": 789},
        }
        mapping_update = {"test": {"test": 456}}
        updated_mapping = {
            "NoChange1": 123,
            "NoChange2": {"Test": 789},
            "test": {"test": 456},
        }

        self.assertDictEqual(
            updated_mapping, deep_update(original_mapping, mapping_update)
        )

    def test_deep_update_list_in_nested_dict(self):
        original_mapping = {
            "test": [{"test1": 123}, {"test2": 456}],
            "test2": [1, 2, 3],
            "NoChange1": 123,
            "NoChange2": {"Test": 789},
            "NoChange3": [0, 9, 8],
        }

        mapping_update = {
            "test": [{"test3": 789}],
            "test2": [4, 5, 6],
        }
        updated_mapping = {
            "test": [{"test1": 123}, {"test2": 456}, {"test3": 789}],
            "test2": [1, 2, 3, 4, 5, 6],
            "NoChange1": 123,
            "NoChange2": {"Test": 789},
            "NoChange3": [0, 9, 8],
        }

        self.assertDictEqual(
            updated_mapping, deep_update(original_mapping, mapping_update)
        )

        # check that existing list entries are not duplicated
        mapping_update = {"test": [{"test2": 456}]}
        updated_mapping = {
            "test": [{"test1": 123}, {"test2": 456}],
            "test2": [1, 2, 3],
            "NoChange1": 123,
            "NoChange2": {"Test": 789},
            "NoChange3": [0, 9, 8],
        }

        self.assertDictEqual(
            updated_mapping, deep_update(original_mapping, mapping_update)
        )

    def test_preservation_of_original_dicts(self):
        original_mapping = {
            "test": [{"test1": 123}, {"test2": 456}],
            "test2": [1, 2, 3],
            "NoChange1": 123,
            "NoChange2": {"Test": 789},
            "NoChange3": [0, 9, 8],
        }

        mapping_update = {"test": [{"test3": 789}], "test2": [4, 5, 6]}
        deep_update(original_mapping, mapping_update)

        self.assertDictEqual(
            original_mapping,
            {
                "test": [{"test1": 123}, {"test2": 456}],
                "test2": [1, 2, 3],
                "NoChange1": 123,
                "NoChange2": {"Test": 789},
                "NoChange3": [0, 9, 8],
            },
        )

        self.assertDictEqual(
            mapping_update, {"test": [{"test3": 789}], "test2": [4, 5, 6]}
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
