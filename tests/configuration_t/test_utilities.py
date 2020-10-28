from tardis.configuration.utilities import enable_yaml_load

from unittest import TestCase

import yaml


@enable_yaml_load("!TestDummy")  # noqa: B903
class TestDummy(object):  # noqa: B903
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class TestEnableYAMLLoad(TestCase):
    def test_enable_yaml_load(self):
        no_args_yml = """!TestDummy"""
        instance = yaml.safe_load(no_args_yml)
        self.assertEqual(instance.args, ())
        self.assertEqual(instance.kwargs, {})

        args_yml = """
        !TestDummy
        - test
        """
        instance = yaml.safe_load(args_yml)
        self.assertEqual(instance.args, ("test",))
        self.assertEqual(instance.kwargs, {})

        kwargs_yml = """
        !TestDummy
        test: test
        """
        instance = yaml.safe_load(kwargs_yml)
        self.assertEqual(instance.args, ())
        self.assertEqual(instance.kwargs, {"test": "test"})
