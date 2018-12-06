from ..configuration.configuration import Configuration
from ..interfaces.observer import Observer
from ..interfaces.state import State

import aiosqlite
import logging
import sqlite3


class SqliteRegistry(Observer):
    def __init__(self):
        configuration = Configuration()
        self._db_file = configuration.SqliteRegistry.db_file
        self._deploy_db_schema()
        self._dispatch_on_state = dict(RequestState=self.insert_resource,
                                       DownState=self.delete_resource)

        for site in configuration.Sites:
            self.add_site(site)
            for machine_type in getattr(configuration, site).MachineTypes:
                self.add_machine_types(site, machine_type)

    def add_machine_types(self, site_name, machine_type):
        sql_query = """INSERT OR IGNORE INTO MachineTypes(machine_type, site_id) 
        SELECT :machine_type, Sites.site_id FROM Sites WHERE Sites.site_name = :site_name"""
        self.execute(sql_query, dict(site_name=site_name, machine_type=machine_type))

    def add_site(self, site_name):
        sql_query = "INSERT OR IGNORE INTO Sites(site_name) VALUES (:site_name)"
        self.execute(sql_query, dict(site_name=site_name))

    async def async_execute(self, sql_query, bind_parameters):
        async with self.connect(flavour=aiosqlite) as connection:
            connection.row_factory = lambda cur, row: {col[0]: row[idx] for idx, col in enumerate(cur.description)}
            async with connection.cursor() as cursor:
                await cursor.execute(sql_query, bind_parameters)
                await connection.commit()
                return await cursor.fetchall()

    def connect(self, flavour):
        return flavour.connect(self._db_file)

    def _deploy_db_schema(self):
        tables = {'MachineTypes': ['machine_type_id INTEGER PRIMARY KEY AUTOINCREMENT',
                                   'machine_type VARCHAR(255) UNIQUE',
                                   'site_id INTEGER',
                                   'FOREIGN KEY(site_id) REFERENCES Sites(site_id)'],
                  'Resources': ['id INTEGER PRIMARY KEY AUTOINCREMENT,'
                                'resource_id VARCHAR(255) UNIQUE',
                                'dns_name VARCHAR(255) UNIQUE',
                                'state_id INTEGER',
                                'site_id INTEGER',
                                'machine_type_id INTEGER',
                                'created DATE',
                                'updated DATE',
                                'FOREIGN KEY(state_id) REFERENCES ResourceState(state_id)',
                                'FOREIGN KEY(site_id) REFERENCES Sites(site_id)',
                                'FOREIGN KEY(machine_type_id) REFERENCES MachineTypes(machine_type_id)'],
                  'ResourceStates': ['state_id INTEGER PRIMARY KEY AUTOINCREMENT',
                                     'state VARCHAR(255) UNIQUE'],
                  'Sites': ['site_id INTEGER PRIMARY KEY AUTOINCREMENT',
                            'site_name VARCHAR(255) UNIQUE']}

        with self.connect(flavour=sqlite3) as connection:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            for table_name, columns in tables.items():
                cursor.execute(f"create table if not exists {table_name} ({', '.join(columns)})")

            for state in State.get_all_states():
                cursor.execute("INSERT OR IGNORE INTO ResourceStates(state) VALUES (?)",
                               (state,))

    async def delete_resource(self, bind_parameters):
        sql_query = """DELETE FROM Resources 
        WHERE resource_id = :resource_id 
        AND site_id = (SELECT site_id from Sites WHERE site_name = :site_name)"""
        await self.async_execute(sql_query, bind_parameters)

    def execute(self, sql_query, bind_parameters):
        with self.connect(flavour=sqlite3) as connection:
            connection.row_factory = lambda cur, row: {col[0]: row[idx] for idx, col in enumerate(cur.description)}
            cursor = connection.cursor()
            cursor.execute(sql_query, bind_parameters)
            return cursor.fetchall()

    def get_resources(self, site_name, machine_type):
        sql_query = """SELECT R.resource_id, R.dns_name, RS.state, R.created, R.updated 
        FROM Resources R
        JOIN ResourceStates RS ON R.state_id = RS.state_id
        JOIN Sites S ON R.site_id = S.site_id
        JOIN MachineTypes MT ON R.machine_type_id = MT.machine_type_id
        WHERE S.site_name = :site_name AND MT.machine_type = :machine_type"""
        return self.execute(sql_query, dict(site_name=site_name, machine_type=machine_type))

    async def insert_resource(self, bind_parameters):
        sql_query = """INSERT OR IGNORE INTO 
        Resources(resource_id, dns_name, state_id, site_id, machine_type_id, created, updated) 
        SELECT :resource_id, :dns_name, RS.state_id, S.site_id, MT.machine_type_id, :created, :updated
        FROM ResourceStates RS
        JOIN Sites S ON S.site_name = :site_name
        JOIN MachineTypes MT ON MT.machine_type = :machine_type AND MT.site_id = S.site_id
        WHERE RS.state = :state"""
        await self.async_execute(sql_query, bind_parameters)

    async def notify(self, state, resource_attributes):
        state = str(state)
        logging.debug(f"Drone: {str(resource_attributes)} has changed state to {state}")
        bind_parameters = dict(state=state)
        bind_parameters.update(resource_attributes)
        await self._dispatch_on_state.get(state, self.update_resource)(bind_parameters)

    async def update_resource(self, bind_parameters):
        sql_query = """UPDATE Resources SET updated = :updated,
        state_id = (SELECT state_id FROM ResourceStates WHERE state = :state) 
        WHERE resource_id = :resource_id 
        AND site_id = (SELECT site_id FROM Sites WHERE site_name = :site_name)"""
        await self.async_execute(sql_query, bind_parameters)
