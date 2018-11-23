from ..interfaces.observer import Observer
from ..interfaces.state import State

import aiosqlite
import logging
import sqlite3


class SqliteRegistry(Observer):
    def __init__(self, db_file):
        self._db_file = db_file
        self._deploy_db_schema()

    def add_machine_types(self, site_name, machine_type):
        with self.connect(flavour=sqlite3) as connection:
            cursor = connection.cursor()
            cursor.execute("""INSERT OR IGNORE INTO MachineTypes(machine_type, site_id) 
                              SELECT ?, Sites.site_id FROM Sites WHERE Sites.site_name = ?""",
                           (machine_type, site_name))

    def add_site(self, site_name):
        with self.connect(flavour=sqlite3) as connection:
            cursor = connection.cursor()
            cursor.execute("INSERT OR IGNORE INTO Sites(site_name) VALUES (?)", (site_name,))

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

    async def notify(self, state, resource_attributes):
        logging.debug(f"Drone: {str(resource_attributes)} has changed state to {state}")
        bind_parameters = dict(state=str(state))
        bind_parameters.update(resource_attributes)

        async with self.connect(flavour=aiosqlite) as connection:
            async with connection.cursor() as cursor:
                try:
                    await cursor.execute("BEGIN TRANSACTION")
                    await cursor.execute("""INSERT OR IGNORE INTO 
                    Resources(resource_id, dns_name, state_id, site_id, machine_type_id, created, updated) 
                    SELECT :resource_id, :dns_name, RS.state_id, S.site_id, MT.machine_type_id, :created, :updated
                    FROM ResourceStates RS
                    JOIN Sites S ON S.site_name = :site_name
                    JOIN MachineTypes MT ON MT.machine_type = :machine_type AND MT.site_id = S.site_id
                    WHERE RS.state = :state""", bind_parameters)
                    await cursor.execute("""UPDATE Resources SET updated = :updated,
                    state_id = (SELECT state_id FROM ResourceStates WHERE state = :state) 
                    WHERE resource_id = :resource_id 
                    AND site_id = (SELECT site_id FROM Sites WHERE site_name = :site_name)""", bind_parameters)
                except aiosqlite.Error as error:
                    await cursor.execute("ROLLBACK")
                    raise error
                else:
                    await cursor.execute("COMMIT")
