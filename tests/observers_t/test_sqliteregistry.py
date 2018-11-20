from tardis.resources.dronestates import RequestState
from tardis.interfaces.state import State
from tardis.observers.sqliteregistry import SqliteRegistry

from unittest import TestCase

import asyncio
import os
import sqlite3


class TestSqliteRegistry(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_site_name = 'MyGreatTestSite'
        cls.test_machine_type = 'MyGreatTestMachineType'
        cls.tables_in_db = {'MachineTypes', 'Resources', 'ResourceState', 'Sites'}

    def setUp(self):
        self.test_path = os.path.dirname(os.path.realpath(__file__))
        self.test_db = os.path.join(self.test_path, 'test.db')
        try:
            os.remove(self.test_db)
        except FileNotFoundError:
            pass

    def test_add_machine_types(self):
        registry = SqliteRegistry(self.test_db)
        registry.add_site(self.test_site_name)
        registry.add_machine_types(self.test_site_name, self.test_machine_type)

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute("""SELECT MachineTypes.machine_type, Sites.site_name FROM MachineTypes 
                              JOIN Sites ON MachineTypes.site_id=Sites.site_id""")
            for row in cursor:
                self.assertEqual(row, (self.test_machine_type, self.test_site_name))

    def test_add_site(self):
        registry = SqliteRegistry(self.test_db)
        registry.add_site(self.test_site_name)

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute('SELECT site_name FROM Sites')
            for row in cursor:
                self.assertEqual(row[0], self.test_site_name)

    def test_connect(self):
        SqliteRegistry(self.test_db)

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            created_tables = {table_name[0] for table_name in cursor.fetchall() if table_name[0] != "sqlite_sequence"}
        self.assertEqual(created_tables, self.tables_in_db)

    def test_double_schema_deployment(self):
        SqliteRegistry(self.test_db)
        SqliteRegistry(self.test_db)

    def test_notify(self):
        registry = SqliteRegistry(self.test_db)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(registry.notify(RequestState(), {}))

    def test_resource_status(self):
        SqliteRegistry(self.test_db)

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT state FROM ResourceState")
            status = {row[0] for row in cursor.fetchall()}

        self.assertEqual(status, {state for state in State.get_all_states()})
