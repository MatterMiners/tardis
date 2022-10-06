from tardis.interfaces.siteadapter import SiteAdapter, SiteAdapterBaseModel
from tardis.utilities.attributedict import AttributeDict

from ..utilities.utilities import run_async

from cobald.utility.primitives import infinity as inf
from unittest import TestCase
from unittest.mock import patch
from pydantic.error_wrappers import ValidationError

import logging


class TestSiteAdapter(TestCase):
    mock_config_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch("tardis.interfaces.siteadapter.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()

    @patch.multiple(SiteAdapter, __abstractmethods__=set())
    def setUp(self) -> None:
        self.config = self.mock_config.return_value
        self.config.Sites = [
            AttributeDict(name="TestSite", adapter="TestSite", quota=1)
        ]
        self.config.TestSite = AttributeDict(
            MachineTypes=["TestMachineType"],
            MachineMetaData=AttributeDict(
                TestMachineType=AttributeDict(Cores=128, Memory=512, Disk=100)
            ),
            MachineTypeConfiguration=AttributeDict(
                TestMachineType=AttributeDict(test_id="abc123")
            ),
        )
        self.site_adapter = SiteAdapter()
        self.site_adapter._site_name = "TestSite"
        self.site_adapter._machine_type = "TestMachineType"
        self.site_adapter._configuration_validation_model = SiteAdapterBaseModel

    def test_configuration(self):
        self.assertEqual(self.site_adapter.configuration, self.config.TestSite)

    def test_configuration_validation_model(self):
        self.assertEqual(
            SiteAdapterBaseModel, self.site_adapter.configuration_validation_model
        )

        # noinspection PyUnresolvedReferences
        del self.site_adapter._configuration_validation_model

        with self.assertRaises(AttributeError):
            # noinspection PyStatementEffect
            self.site_adapter.configuration_validation_model

    def test_deploy_resource(self):
        with self.assertRaises(NotImplementedError):
            run_async(self.site_adapter.deploy_resource, dict())

    def test_drone_environment(self):
        self.assertEqual(
            AttributeDict(Cores=128, Memory=524288, Disk=104857600, Uuid="test-123"),
            self.site_adapter.drone_environment(
                drone_uuid="test-123",
                meta_data_translation_mapping=AttributeDict(
                    Cores=1,
                    Memory=1024,
                    Disk=1024 * 1024,
                ),
            ),
        )

        with self.assertLogs(
            logger="cobald.runtime.tardis.utilities.utils", level=logging.CRITICAL
        ), self.assertRaises(KeyError):
            self.site_adapter.drone_environment(
                drone_uuid="test-123",
                meta_data_translation_mapping=AttributeDict(
                    Memory=1024,
                    Disk=1024 * 1024,
                ),
            )

    def test_drone_heartbeat_interval(self):
        self.assertEqual(self.site_adapter.drone_heartbeat_interval, 60)

        # lru_cache needs to be cleared before manipulating site configuration
        self.site_adapter.refresh_configuration()

        self.config.Sites[0]["drone_heartbeat_interval"] = 10
        self.assertEqual(self.site_adapter.drone_heartbeat_interval, 10)

        self.site_adapter.refresh_configuration()

        self.config.Sites[0]["drone_heartbeat_interval"] = -1
        with self.assertRaises(ValidationError):
            # noinspection PyStatementEffect
            self.site_adapter.drone_heartbeat_interval

    def test_drone_minimum_lifetime(self):
        self.assertEqual(self.site_adapter.drone_minimum_lifetime, None)

        # lru_cache needs to be cleared before manipulating site configuration
        self.site_adapter.refresh_configuration()

        self.config.Sites[0]["drone_minimum_lifetime"] = 10
        self.assertEqual(self.site_adapter.drone_minimum_lifetime, 10)

        # noinspection PyUnresolvedReferences
        self.site_adapter.refresh_configuration()

        self.config.Sites[0]["drone_minimum_lifetime"] = -1
        with self.assertRaises(ValidationError):
            # noinspection PyStatementEffect
            self.site_adapter.drone_minimum_lifetime

    def test_drone_uuid(self):
        self.assertEqual(
            "testsite-test123", self.site_adapter.drone_uuid(uuid="test123")
        )

    def test_handle_exception(self):
        with self.assertRaises(NotImplementedError):
            self.site_adapter.handle_exceptions()

    def test_handle_response_matching(self):
        test_response = {"test": 123}
        test_key_translator = {"new_test": "test"}
        test_translator_functions = {"test": str}

        self.assertEqual(
            self.site_adapter.handle_response(
                test_response, test_key_translator, test_translator_functions
            ),
            AttributeDict(new_test="123"),
        )

        self.assertEqual(
            self.site_adapter.handle_response(
                test_response,
                test_key_translator,
                test_translator_functions,
                additional="test123",
            ),
            AttributeDict(new_test="123", additional="test123"),
        )

    def test_handle_response_non_matching(self):
        test_response = {"other_test": 123}
        test_key_translator = {"new_test": "test"}
        test_translator_functions = {"test": str}

        self.assertEqual(
            self.site_adapter.handle_response(
                test_response, test_key_translator, test_translator_functions
            ),
            AttributeDict(),
        )

        self.assertEqual(
            self.site_adapter.handle_response(
                test_response,
                test_key_translator,
                test_translator_functions,
                additional="test123",
            ),
            AttributeDict(additional="test123"),
        )

    def test_machine_meta_data(self):
        self.assertEqual(
            self.site_adapter.machine_meta_data,
            AttributeDict(Cores=128, Memory=512, Disk=100),
        )

        # noinspection PyUnresolvedReferences
        del self.site_adapter._machine_type

        with self.assertRaises(AttributeError):
            # noinspection PyStatementEffect
            self.site_adapter.machine_meta_data

    def test_machine_meta_data_validation(self):
        def assert_raised_validation_error_existence(meta_data_entry):
            self.site_adapter.refresh_configuration()
            with self.assertRaises(ValidationError) as ve:
                # noinspection PyStatementEffect
                self.site_adapter.configuration
            self.assertTrue(
                f"You have to supply the {meta_data_entry} entry in the "
                f"MachineMetaData for MachineType TestMachineType!"
                in ve.exception.errors()[0]["msg"]
            )

        def assert_raised_validation_error_wrong_type(meta_data_entry):
            self.site_adapter.refresh_configuration()
            with self.assertRaises(ValidationError) as ve:
                # noinspection PyStatementEffect
                self.site_adapter.configuration
            self.assertTrue(
                "You supplied a wrong type <class 'str'> in the "
                "MachineMetaData for machine_type TestMachineType entry "
                f"'{meta_data_entry}: 123'!\n"
                f"The allowed types are " in ve.exception.errors()[0]["msg"]
            )

        for meta_data_entry in ("Cores", "Disk", "Memory"):
            current_meta_data_entry = getattr(
                self.config.TestSite.MachineMetaData.TestMachineType,
                meta_data_entry,
            )
            setattr(
                self.config.TestSite.MachineMetaData.TestMachineType,
                meta_data_entry,
                "123",
            )
            assert_raised_validation_error_wrong_type(meta_data_entry)

            delattr(
                self.config.TestSite.MachineMetaData.TestMachineType, meta_data_entry
            )
            assert_raised_validation_error_existence(meta_data_entry)
            setattr(
                self.config.TestSite.MachineMetaData.TestMachineType,
                meta_data_entry,
                current_meta_data_entry,
            )

    def test_machine_type(self):
        self.assertEqual(self.site_adapter.machine_type, "TestMachineType")

        # noinspection PyUnresolvedReferences
        del self.site_adapter._machine_type

        with self.assertRaises(AttributeError):
            # noinspection PyStatementEffect
            self.site_adapter.machine_type

    def test_machine_type_configuration_and_meta_data_existence(self):
        def assert_raised_validation_error(config_block):
            self.site_adapter.refresh_configuration()
            with self.assertRaises(ValidationError) as ve:
                # noinspection PyStatementEffect
                self.site_adapter.configuration
            self.assertTrue(
                f"You have to specify {config_block} for MachineType TestMachineType"  # noqa B950
                in ve.exception.errors()[0]["msg"]
            )

        for config_block in ("MachineTypeConfiguration", "MachineMetaData"):
            current_config_block = AttributeDict(
                getattr(self.config.TestSite, config_block)
            )
            del getattr(self.config.TestSite, config_block).TestMachineType
            assert_raised_validation_error(config_block)

            setattr(self.config.TestSite, config_block, current_config_block)
            delattr(self.config.TestSite, config_block)
            assert_raised_validation_error(config_block)

            setattr(self.config.TestSite, config_block, current_config_block)

    def test_machine_type_validation_not_exists(self):
        del self.config.TestSite.MachineTypes
        self.site_adapter.refresh_configuration()
        with self.assertRaises(ValidationError) as ve:
            # noinspection PyStatementEffect
            self.site_adapter.configuration
        self.assertTrue(
            "You have to add MachineTypes to the site configuration"
            in ve.exception.errors()[0]["msg"]
        )

    def test_machine_type_configuration(self):
        self.assertEqual(
            self.site_adapter.machine_type_configuration,
            AttributeDict(test_id="abc123"),
        )

        # noinspection PyUnresolvedReferences
        del self.site_adapter._machine_type

        with self.assertRaises(AttributeError):
            # noinspection PyStatementEffect
            self.site_adapter.machine_type_configuration

    def test_refresh_configuration(self):
        current_config = self.site_adapter.site_configuration
        self.config.Sites[0]["quota"] = 123
        self.assertEqual(current_config, self.site_adapter.site_configuration)
        self.site_adapter.refresh_configuration()
        current_config["quota"] = 123
        self.assertEqual(current_config, self.site_adapter.site_configuration)

        current_config = self.site_adapter.configuration
        self.config.TestSite.MachineTypeConfiguration.TestMachineType.test_id = "xy789"
        self.assertEqual(current_config, self.site_adapter.configuration)
        self.site_adapter.refresh_configuration()
        current_config.MachineTypeConfiguration.TestMachineType.test_id = "xy789"
        self.assertEqual(current_config, self.site_adapter.configuration)

    def test_resource_status(self):
        with self.assertRaises(NotImplementedError):
            run_async(self.site_adapter.resource_status, dict())

    def test_site_configuration(self):
        self.assertEqual(
            self.site_adapter.site_configuration,
            AttributeDict(
                name="TestSite",
                adapter="TestSite",
                quota=1,
                drone_minimum_lifetime=None,
                drone_heartbeat_interval=60,
            ),
        )

        self.site_adapter.refresh_configuration()

        del self.config.Sites[0]["quota"]

        self.assertEqual(
            self.site_adapter.site_configuration,
            AttributeDict(
                name="TestSite",
                adapter="TestSite",
                quota=inf,
                drone_minimum_lifetime=None,
                drone_heartbeat_interval=60,
            ),
        )

        self.site_adapter.refresh_configuration()

        self.config.Sites[0]["extra"] = "Should fail!"

        with self.assertRaises(ValidationError):
            self.assertEqual(
                self.site_adapter.site_configuration,
                AttributeDict(
                    name="TestSite",
                    adapter="TestSite",
                    quota=inf,
                    drone_minimum_lifetime=None,
                    drone_heartbeat_interval=60,
                ),
            )

        self.site_adapter.refresh_configuration()

        self.config.Sites[0]["quota"] = 0

        with self.assertRaises(ValidationError):
            # noinspection PyStatementEffect
            self.site_adapter.site_configuration

    def test_site_name(self):
        self.assertEqual(self.site_adapter.site_name, "TestSite")
        del self.site_adapter._site_name

        with self.assertRaises(AttributeError):
            # noinspection PyStatementEffect
            self.site_adapter.site_name

    def test_stop_resource(self):
        with self.assertRaises(NotImplementedError):
            run_async(self.site_adapter.stop_resource, dict())

    def test_terminate_resource(self):
        with self.assertRaises(NotImplementedError):
            run_async(self.site_adapter.terminate_resource, dict())
