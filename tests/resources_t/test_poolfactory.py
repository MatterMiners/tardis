from tardis.resources.dronestates import RequestState
from tardis.resources.poolfactory import create_composite_pool
from tardis.resources.poolfactory import create_drone
from tardis.resources.poolfactory import get_drones_to_restore
from tardis.resources.poolfactory import load_plugins
from tardis.resources.poolfactory import str_to_state
from tardis.utilities.attributedict import AttributeDict

from unittest import TestCase
from unittest.mock import ANY, MagicMock, call, patch


class TestPoolFactory(TestCase):
    mock_config_patcher = None
    mock_sqliteregistry_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch("tardis.resources.poolfactory.Configuration")
        cls.mock_sqliteregistry_patcher = patch(
            "tardis.plugins.sqliteregistry.SqliteRegistry"
        )
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_sqliteregistry = cls.mock_sqliteregistry_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_sqliteregistry_patcher.stop()

    def setUp(self):
        self.config = self.mock_config.return_value
        self.config.Sites = [
            AttributeDict(name="TestSite", adapter="TestSite", quota=1)
        ]
        self.config.TestSite = AttributeDict(
            MachineTypes=["TestMachineType"],
            MachineMetaData=AttributeDict(TestMachineType=AttributeDict(Cores=1)),
        )
        self.config.Plugins = AttributeDict(
            SqliteRegistry=AttributeDict(db_file="test.db")
        )
        self.config.BatchSystem = AttributeDict(adapter="TestBatchSystem")
        sqlite_registry = self.mock_sqliteregistry.return_value
        sqlite_registry.get_resources.return_value = [{"state": "RequestState"}]

    def test_str_to_state(self):
        test = [{"state": "RequestState", "drone_uuid": "test-abc123"}]
        converted_test = str_to_state(test)
        self.assertTrue(converted_test[0]["state"], RequestState)
        self.assertEqual(converted_test[0]["drone_uuid"], "test-abc123")

    @patch("tardis.resources.poolfactory.FactoryPool")
    @patch("tardis.resources.poolfactory.Logger")
    @patch("tardis.resources.poolfactory.Standardiser")
    @patch("tardis.resources.poolfactory.WeightedComposite")
    @patch("tardis.resources.poolfactory.import_module")
    def test_create_composite(
        self,
        mock_import_module,
        mock_weighted_composite,
        mock_standardiser,
        mock_logger,
        mock_factory_pool,
    ):
        mock_batch_system_adapter = AttributeDict(TestBatchSystemAdapter=MagicMock())
        mock_site_adapter = AttributeDict(TestSiteAdapter=MagicMock())

        mock_import_module.side_effect = [
            mock_batch_system_adapter,
            self.mock_sqliteregistry,
            mock_site_adapter,
        ]

        self.assertEqual(create_composite_pool(), mock_weighted_composite())

        self.assertEqual(
            mock_import_module.mock_calls,
            [
                call(name="tardis.adapters.batchsystems.testbatchsystem"),
                call(name="tardis.plugins.sqliteregistry"),
                call(name="tardis.adapters.sites.testsite"),
            ],
        )

        site_name = self.config.Sites[0].name
        machine_type = getattr(self.config, site_name).MachineTypes[0]

        mock_batch_system_adapter.TestBatchSystemAdapter.assert_called_with()
        mock_site_adapter.TestSiteAdapter.assert_called_with(
            machine_type=machine_type, site_name=site_name
        )

        self.assertEqual(mock_factory_pool.mock_calls, [call(factory=ANY)])

        cpu_cores = getattr(
            self.config, site_name
        ).MachineMetaData.TestMachineType.Cores

        self.assertEqual(
            mock_standardiser.mock_calls,
            [
                call(mock_factory_pool(), minimum=cpu_cores, granularity=cpu_cores),
                call(mock_weighted_composite(), maximum=self.config.Sites[0].quota),
            ],
        )

        self.assertEqual(
            mock_logger.mock_calls,
            [
                call(
                    mock_standardiser(),
                    name=f"{site_name.lower()}_{machine_type.lower()}",
                )
            ],
        )

        mock_weighted_composite.has_calls(
            [
                call(mock_standardiser(), weight="utilisation"),
                call(mock_weighted_composite(), weight="utilisation"),
            ]
        )

    @patch("tardis.resources.poolfactory.Drone")
    @patch("tardis.resources.poolfactory.BatchSystemAgent")
    @patch("tardis.resources.poolfactory.SiteAgent")
    def test_create_drone(self, mock_site_agent, mock_batch_system_agent, mock_drone):
        self.assertEqual(
            create_drone(
                site_agent=mock_site_agent, batch_system_agent=mock_batch_system_agent
            ),
            mock_drone(),
        )

        mock_drone.has_call(
            [
                call(
                    site_agent=mock_site_agent,
                    batch_system_agent=mock_batch_system_agent,
                    plugins=None,
                    remote_resource_uuid=None,
                    drone_uuid=None,
                    state=RequestState(),
                    created=None,
                    updated=None,
                )
            ]
        )

    def test_load_plugins(self):
        self.assertEqual(load_plugins(), {"SqliteRegistry": self.mock_sqliteregistry()})

        self.mock_config.side_effect = AttributeError
        self.assertEqual(load_plugins(), {})
        self.mock_config.side_effect = None

    def test_get_drones_to_restore(self):
        self.assertEqual(
            get_drones_to_restore(
                plugins={}, site=self.config.Sites[0], machine_type="TestMachineType"
            ),
            [],
        )

        self.assertIsInstance(
            get_drones_to_restore(
                plugins={"SqliteRegistry": self.mock_sqliteregistry()},
                site=self.config.Sites[0],
                machine_type="TestMachineType",
            )[0]["state"],
            RequestState,
        )
