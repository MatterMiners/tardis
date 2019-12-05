from tardis.interfaces.siteadapter import SiteAdapter
from tardis.utilities.attributedict import AttributeDict

from ..utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import patch


class TestSiteAdapter(TestCase):
    @patch.multiple(SiteAdapter, __abstractmethods__=set())
    def setUp(self) -> None:
        self.site_adapter = SiteAdapter()

    def test_configuration(self):
        with self.assertRaises(AttributeError):
            self.site_adapter.configuration

    def test_deploy_resource(self):
        with self.assertRaises(NotImplementedError):
            run_async(self.site_adapter.deploy_resource, dict())

    def test_handle_exception(self):
        with self.assertRaises(NotImplementedError):
            self.site_adapter.handle_exceptions()

    def test_handle_response_matching(self):
        test_response = {"test": 123}
        test_key_translator = {"new_test": "test"}
        test_translator_functions = {"test": str}
        self.assertEqual(
            self.site_adapter.handle_response(
                test_response,
                test_key_translator,
                test_translator_functions,
                additional="test123",
            ),
            AttributeDict(new_test="123", additional="test123"),
        )

    def test_handle_response_non_matching_with_additional(self):
        test_response = {"other_test": 123}
        test_key_translator = {"new_test": "test"}
        test_translator_functions = {"test": str}

        self.assertEqual(
            self.site_adapter.handle_response(
                test_response,
                test_key_translator,
                test_translator_functions,
                additional="test123",
            ),
            AttributeDict(additional="test123"),
        )

    def test_handle_response_non_matching_wo_additional(self):
        test_response = {"other_test": 123}
        test_key_translator = {"new_test": "test"}
        test_translator_functions = {"test": str}

        self.assertEqual(
            self.site_adapter.handle_response(
                test_response, test_key_translator, test_translator_functions
            ),
            AttributeDict(),
        )

    def test_machine_type(self):
        with self.assertRaises(AttributeError):
            self.site_adapter.machine_type

    def test_resource_status(self):
        with self.assertRaises(NotImplementedError):
            run_async(self.site_adapter.resource_status, dict())

    def test_site_name(self):
        with self.assertRaises(AttributeError):
            self.site_adapter.site_name

    def test_stop_resource(self):
        with self.assertRaises(NotImplementedError):
            run_async(self.site_adapter.stop_resource, dict())

    def test_terminate_resource(self):
        with self.assertRaises(NotImplementedError):
            run_async(self.site_adapter.terminate_resource, dict())
