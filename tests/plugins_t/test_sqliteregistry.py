from tardis.resources.dronestates import BootingState
from tardis.resources.dronestates import IntegrateState
from tardis.resources.dronestates import DownState
from tardis.interfaces.state import State
from tardis.plugins.sqliteregistry import SqliteRegistry
from tardis.utilities.attributedict import AttributeDict
from ..utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import patch
from unittest.mock import Mock

import datetime
import os
import sqlite3


class TestSqliteRegistry(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_site_name = "MyGreatTestSite"
        cls.test_machine_type = "MyGreatTestMachineType"
        cls.tables_in_db = {"MachineTypes", "Resources", "ResourceStates", "Sites"}
        cls.test_resource_attributes = {
            "remote_resource_uuid": "bf85022b-fdd6-42b1-932d-086c288d4755",
            "drone_uuid": f"{cls.test_site_name}-07af52405e",
            "site_name": cls.test_site_name,
            "machine_type": cls.test_machine_type,
            "created": datetime.datetime(2018, 11, 16, 15, 49, 58),
            "updated": datetime.datetime(2018, 11, 16, 15, 49, 58),
        }
        cls.test_updated_resource_attributes = {
            "remote_resource_uuid": "bf85022b-fdd6-42b1-932d-086c288d4755",
            "drone_uuid": f"{cls.test_site_name}-07af52405e",
            "site_name": cls.test_site_name,
            "machine_type": cls.test_machine_type,
            "created": datetime.datetime(2018, 11, 16, 15, 49, 58),
            "updated": datetime.datetime(2018, 11, 16, 15, 50, 58),
        }

        cls.test_get_resources_result = {
            "remote_resource_uuid": cls.test_resource_attributes[
                "remote_resource_uuid"
            ],
            "drone_uuid": cls.test_resource_attributes["drone_uuid"],
            "state": str(BootingState()),
            "created": cls.test_resource_attributes["created"],
            "updated": cls.test_resource_attributes["updated"],
        }

        cls.test_notify_result = (
            cls.test_resource_attributes["remote_resource_uuid"],
            cls.test_resource_attributes["drone_uuid"],
            str(BootingState()),
            cls.test_resource_attributes["site_name"],
            cls.test_resource_attributes["machine_type"],
            str(cls.test_resource_attributes["created"]),
            str(cls.test_resource_attributes["updated"]),
        )

        cls.test_updated_notify_result = (
            cls.test_updated_resource_attributes["remote_resource_uuid"],
            cls.test_updated_resource_attributes["drone_uuid"],
            str(IntegrateState()),
            cls.test_updated_resource_attributes["site_name"],
            cls.test_updated_resource_attributes["machine_type"],
            str(cls.test_updated_resource_attributes["created"]),
            str(cls.test_updated_resource_attributes["updated"]),
        )

        cls.mock_config_patcher = patch("tardis.plugins.sqliteregistry.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()

    def setUp(self):
        self.test_path = os.path.dirname(os.path.realpath(__file__))
        self.test_db = os.path.join(self.test_path, "test.db")
        try:
            os.remove(self.test_db)
        except FileNotFoundError:
            pass

        config = self.mock_config.return_value
        config.Plugins.SqliteRegistry.db_file = self.test_db
        config.Sites = [AttributeDict(name=self.test_site_name)]
        getattr(config, self.test_site_name).MachineTypes = [self.test_machine_type]

    def test_add_machine_types(self):
        registry = SqliteRegistry()
        registry.add_site(self.test_site_name)
        registry.add_machine_types(self.test_site_name, self.test_machine_type)

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT MachineTypes.machine_type, Sites.site_name FROM MachineTypes
                              JOIN Sites ON MachineTypes.site_id=Sites.site_id"""
            )
            for row in cursor:
                self.assertEqual(row, (self.test_machine_type, self.test_site_name))

    def test_add_site(self):
        registry = SqliteRegistry()
        registry.add_site(self.test_site_name)

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT site_name FROM Sites")
            for row in cursor:
                self.assertEqual(row[0], self.test_site_name)

    def test_connect(self):
        SqliteRegistry()

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            created_tables = {
                table_name[0]
                for table_name in cursor.fetchall()
                if table_name[0] != "sqlite_sequence"
            }
        self.assertEqual(created_tables, self.tables_in_db)

    def test_double_schema_deployment(self):
        SqliteRegistry()
        SqliteRegistry()

    @patch("tardis.plugins.sqliteregistry.logging", Mock())
    def test_get_resources(self):
        registry = SqliteRegistry()
        registry.add_site(self.test_site_name)
        registry.add_machine_types(self.test_site_name, self.test_machine_type)
        run_async(registry.notify, BootingState(), self.test_resource_attributes)

        self.assertListEqual(
            registry.get_resources(
                site_name=self.test_site_name, machine_type=self.test_machine_type
            ),
            [self.test_get_resources_result],
        )

    @patch("tardis.plugins.sqliteregistry.logging", Mock())
    def test_notify(self):
        def fetch_row(db):
            with sqlite3.connect(db) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    """SELECT R.remote_resource_uuid, R.drone_uuid, RS.state,
                S.site_name, MT.machine_type, R.created, R.updated
                FROM Resources R
                JOIN ResourceStates RS ON R.state_id = RS.state_id
                JOIN Sites S ON R.site_id = S.site_id
                JOIN MachineTypes MT ON R.machine_type_id = MT.machine_type_id"""
                )
                return cursor.fetchone()

        registry = SqliteRegistry()
        registry.add_site(self.test_site_name)
        registry.add_machine_types(self.test_site_name, self.test_machine_type)

        run_async(registry.notify, BootingState(), self.test_resource_attributes)

        self.assertEqual(self.test_notify_result, fetch_row(self.test_db))

        run_async(
            registry.notify, IntegrateState(), self.test_updated_resource_attributes
        )

        self.assertEqual(self.test_updated_notify_result, fetch_row(self.test_db))

        run_async(registry.notify, DownState(), self.test_updated_resource_attributes)

        self.assertIsNone(fetch_row(self.test_db))

    def test_resource_status(self):
        SqliteRegistry()

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT state FROM ResourceStates")
            status = {row[0] for row in cursor.fetchall()}

        self.assertEqual(status, {state for state in State.get_all_states()})
