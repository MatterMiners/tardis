from tardis.observers.sqliteregistry import SqliteRegistry

from unittest import TestCase

import os
import sqlite3


class TestSqliteRegistry(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_site_name = 'MyGreatTestSite'
        cls.test_machine_type = 'MyGreatTestMachineType'
        cls.tables_in_db = {'MachineTypes', 'Resources', 'ResourceStatus', 'Sites'}

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
