from tardis.resources.dronestates import RequestState
from tardis.resources.dronestates import BootingState
from tardis.interfaces.state import State
from tardis.observers.sqliteregistry import SqliteRegistry

from unittest import TestCase

import asyncio
import datetime
import os
import sqlite3


class TestSqliteRegistry(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_site_name = 'MyGreatTestSite'
        cls.test_machine_type = 'MyGreatTestMachineType'
        cls.tables_in_db = {'MachineTypes', 'Resources', 'ResourceStates', 'Sites'}
        cls.test_resource_attributes = {'resource_id': 'bf85022b-fdd6-42b1-932d-086c288d4755',
                                        'dns_name': f'{cls.test_site_name}-07af52405e',
                                        'site_name': cls.test_site_name,
                                        'machine_type': cls.test_machine_type,
                                        'created': datetime.datetime(2018, 11, 16, 15, 49, 58),
                                        'updated': datetime.datetime(2018, 11, 16, 15, 49, 58)}
        cls.test_updated_resource_attributes = {'resource_id': 'bf85022b-fdd6-42b1-932d-086c288d4755',
                                                'dns_name': f'{cls.test_site_name}-07af52405e',
                                                'site_name': cls.test_site_name,
                                                'machine_type': cls.test_machine_type,
                                                'created': datetime.datetime(2018, 11, 16, 15, 49, 58),
                                                'updated': datetime.datetime(2018, 11, 16, 15, 50, 58)}

        cls.test_notify_result = (cls.test_resource_attributes['resource_id'],
                                  cls.test_resource_attributes['dns_name'],
                                  str(RequestState()),
                                  cls.test_resource_attributes['site_name'],
                                  cls.test_resource_attributes['machine_type'],
                                  str(cls.test_resource_attributes['created']),
                                  str(cls.test_resource_attributes['updated']))

        cls.test_updated_notify_result = (cls.test_updated_resource_attributes['resource_id'],
                                          cls.test_updated_resource_attributes['dns_name'],
                                          str(BootingState()),
                                          cls.test_updated_resource_attributes['site_name'],
                                          cls.test_updated_resource_attributes['machine_type'],
                                          str(cls.test_updated_resource_attributes['created']),
                                          str(cls.test_updated_resource_attributes['updated']))


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
        registry.add_site(self.test_site_name)
        registry.add_machine_types(self.test_site_name, self.test_machine_type)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(registry.notify(RequestState(), self.test_resource_attributes))

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute("""SELECT R.resource_id, R.dns_name, RS.state, S.site_name, MT.machine_type, R.created,
            R.updated
            FROM Resources R
            JOIN ResourceStates RS ON R.state_id = RS.state_id
            JOIN Sites S ON R.site_id = S.site_id
            JOIN MachineTypes MT ON R.machine_type_id = MT.machine_type_id""")
            self.assertEqual(self.test_notify_result, cursor.fetchone())

        loop.run_until_complete(registry.notify(BootingState(), self.test_updated_resource_attributes))

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute("""SELECT R.resource_id, R.dns_name, RS.state, S.site_name, MT.machine_type, R.created,
            R.updated
            FROM Resources R
            JOIN ResourceStates RS ON R.state_id = RS.state_id
            JOIN Sites S ON R.site_id = S.site_id
            JOIN MachineTypes MT ON R.machine_type_id = MT.machine_type_id""")
            self.assertEqual(self.test_updated_notify_result, cursor.fetchone())

    def test_resource_status(self):
        SqliteRegistry(self.test_db)

        with sqlite3.connect(self.test_db) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT state FROM ResourceStates")
            status = {row[0] for row in cursor.fetchall()}

        self.assertEqual(status, {state for state in State.get_all_states()})
