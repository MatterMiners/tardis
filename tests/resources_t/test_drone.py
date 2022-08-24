from ..utilities.utilities import async_return, run_async, set_awaitable_return_value

from tardis.interfaces.plugin import Plugin
from tardis.interfaces.state import State
from tardis.resources.drone import Drone
from tardis.resources.dronestates import DrainState, DownState
from tardis.plugins.sqliteregistry import SqliteRegistry
from tardis.utilities.attributedict import AttributeDict

from logging import DEBUG
from unittest import TestCase
from unittest.mock import MagicMock, patch


class TestDrone(TestCase):
    mock_batch_system_agent_patcher = None
    mock_site_agent_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_site_agent_patcher = patch("tardis.agents.siteagent.SiteAgent")
        cls.mock_site_agent = cls.mock_site_agent_patcher.start()

        cls.mock_batch_system_agent_patcher = patch(
            "tardis.agents.batchsystemagent.BatchSystemAgent"
        )
        cls.mock_batch_system_agent = cls.mock_batch_system_agent_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mock_batch_system_agent_patcher.stop()
        cls.mock_site_agent_patcher.stop()

    def setUp(self) -> None:
        self.mock_site_agent.machine_meta_data = AttributeDict(Cores=8)
        self.mock_site_agent.drone_minimum_lifetime = None
        self.mock_site_agent.drone_heartbeat_interval = 60
        self.mock_plugin = MagicMock(spec=Plugin)()
        self.mock_plugin.notify.return_value = async_return()
        self.drone = Drone(
            site_agent=self.mock_site_agent,
            batch_system_agent=self.mock_batch_system_agent,
        )

    def test_allocation(self):
        self.assertEqual(self.drone.allocation, 0.0)
        self.drone._allocation = 1.0
        self.assertEqual(self.drone.allocation, 1.0)

    def test_batch_system_agent(self):
        self.assertEqual(self.drone.batch_system_agent, self.mock_batch_system_agent)

    def test_database(self):
        self.assertIsNone(self.drone._database)

        sql_registry = MagicMock(spec=SqliteRegistry)
        self.drone.register_plugins(sql_registry)
        self.drone.__dict__.pop("_database")  # reset cached_property's cache

        self.assertEqual(self.drone._database, sql_registry)

    def test_database_state(self):
        self.assertIsNone(run_async(self.drone.database_state))

        sql_registry = MagicMock(spec=SqliteRegistry)
        self.drone.register_plugins(sql_registry)
        self.drone.__dict__.pop("_database")  # reset cached_property's cache
        set_awaitable_return_value(
            sql_registry.get_resource_state, [{"state": "DrainState"}]
        )

        self.assertIsInstance(run_async(self.drone.database_state), DrainState)

        # testing IndexError
        set_awaitable_return_value(sql_registry.get_resource_state, [])
        self.assertIsNone(run_async(self.drone.database_state))

        # testing AttributeError
        delattr(self.drone.resource_attributes, "drone_uuid")
        self.assertIsNone(run_async(self.drone.database_state))

    def test_demand(self):
        self.assertEqual(self.drone.demand, 8)
        self.drone.demand = 0
        self.assertEqual(self.drone.demand, 0)

    def test_heartbeat_interval(self):
        self.assertEqual(self.drone.heartbeat_interval, 60)
        self.mock_site_agent.drone_heartbeat_interval = 10
        self.assertEqual(self.drone.heartbeat_interval, 10)

    def test_life_time(self):
        self.assertIsNone(self.drone.minimum_lifetime, None)
        self.mock_site_agent.drone_minimum_lifetime = 3600
        self.assertEqual(self.drone.minimum_lifetime, 3600)

    def test_maximum_demand(self):
        self.assertEqual(self.drone.maximum_demand, 8)
        self.mock_site_agent.machine_meta_data = AttributeDict(Cores=4)
        self.assertEqual(self.drone.maximum_demand, 4)

    def test_supply(self):
        self.assertEqual(self.drone.supply, 0.0)
        self.drone._supply = 8.0
        self.assertEqual(self.drone.supply, 8.0)

    def test_utilisation(self):
        self.assertEqual(self.drone.utilisation, 0.0)
        self.drone._utilisation = 8.0
        self.assertEqual(self.drone.utilisation, 8.0)

    def test_site_agent(self):
        self.assertEqual(self.drone.site_agent, self.mock_site_agent)

    @patch("tardis.resources.drone.asyncio.sleep")
    def test_run(self, mocked_asyncio_sleep):
        mocked_asyncio_sleep.side_effect = async_return
        mocked_down_state = MagicMock(spec=DownState)
        mocked_down_state.run.return_value = async_return()

        async def mocked_run(drone):
            await drone.set_state(mocked_down_state)

        mocked_state = MagicMock(spec=State)
        mocked_state.run.side_effect = mocked_run

        run_async(self.drone.set_state, mocked_state)
        self.drone.demand = 8
        self.mock_site_agent.drone_heartbeat_interval = 10
        with self.assertLogs(level=DEBUG):
            run_async(self.drone.run)

        # duration skipped via asyncio.sleep
        # use the `sum` to avoid `asyncio.sleep(0)` context switches to skew the result
        mock_elapsed = sum(args[0] for args, _ in mocked_asyncio_sleep.call_args_list)
        self.assertEqual(mock_elapsed, self.mock_site_agent.drone_heartbeat_interval)

        self.assertIsInstance(self.drone.state, DownState)
        self.assertEqual(self.drone.demand, 0)

        mocked_state.run.assert_called_once()
        mocked_down_state.run.assert_called_once()

    def test_register_plugins(self):
        self.assertEqual(self.drone._plugins, [])
        self.drone.register_plugins(self.mock_plugin)
        self.assertEqual(self.drone._plugins, [self.mock_plugin])

    def test_removal_plugins(self):
        self.drone.register_plugins(self.mock_plugin)
        self.assertEqual(self.drone._plugins, [self.mock_plugin])
        self.drone.remove_plugins(self.mock_plugin)
        self.assertEqual(self.drone._plugins, [])

    def test_set_state(self):
        self.drone.register_plugins(self.mock_plugin)
        old_update_time_stamp = self.drone.resource_attributes.updated
        run_async(self.drone.set_state, self.drone._state)
        self.mock_plugin.notify.assert_not_called()
        self.assertEqual(self.drone.resource_attributes.updated, old_update_time_stamp)

        new_state = DownState()
        run_async(self.drone.set_state, new_state)
        self.mock_plugin.notify.assert_called_with(
            new_state, self.drone.resource_attributes
        )
        self.assertNotEqual(
            self.drone.resource_attributes.updated, old_update_time_stamp
        )

    def test_state(self):
        self.assertEqual(self.drone.state, self.drone._state)
        self.assertIsNone(self.drone.state)

    def test_notify_plugins(self):
        self.drone.register_plugins(self.mock_plugin)
        self.assertEqual(self.drone._plugins, [self.mock_plugin])

        run_async(self.drone.notify_plugins)
        self.mock_plugin.notify.assert_called_with(
            self.drone.state, self.drone.resource_attributes
        )
