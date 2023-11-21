from tardis.utilities.attributedict import AttributeDict
from ..configuration.configuration import Configuration
from ..interfaces.plugin import Plugin
from ..interfaces.state import State

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import List, Dict, Generator
import asyncio
import logging
import sqlite3

logger = logging.getLogger("cobald.runtime.tardis.plugins.sqliteregistry")


class SqliteRegistry(Plugin):
    thread_pool_executor = ThreadPoolExecutor(max_workers=1)

    def __init__(self):
        """
        The :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` implements
        a persistent storage of all Drone states in a SQLite database. The usage
        of this module is recommended in order to recover the last state of
        TARDIS in case the service has to be restarted.
        """
        configuration = Configuration()
        self._db_file = configuration.Plugins.SqliteRegistry.db_file
        self._deploy_db_schema()
        self._dispatch_on_state = dict(
            RequestState=self.insert_resource, DownState=self.delete_resource
        )

        for site in configuration.Sites:
            self.add_site(site.name)
            for machine_type in getattr(configuration, site.name).MachineTypes:
                self.add_machine_types(site.name, machine_type)

    def add_machine_types(self, site_name: str, machine_type: str) -> None:
        if self._get_machine_type(site_name, machine_type):
            logger.debug(
                f"{machine_type} is already present for {site_name} in database! Skipping insertion!"  # noqa B950
            )
            return
        sql_query = """
        INSERT OR ROLLBACK INTO MachineTypes(machine_type, site_id)
        SELECT :machine_type, Sites.site_id FROM Sites
        WHERE Sites.site_name = :site_name"""
        self.execute(sql_query, {"site_name": site_name, "machine_type": machine_type})

    def _get_machine_type(self, site_name: str, machine_type: str) -> List[Dict]:
        sql_query = """
        SELECT * FROM MachineTypes MT
        JOIN Sites S ON MT.site_id = S.site_id
        WHERE MT.machine_type = :machine_type AND S.site_name = :site_name"""
        return self.execute(
            sql_query, {"site_name": site_name, "machine_type": machine_type}
        )

    def add_site(self, site_name: str) -> None:
        if self._get_site(site_name):
            logger.debug(
                f"{site_name} already present in database! Skipping insertion!"
            )
            return
        sql_query = "INSERT OR ROLLBACK INTO Sites(site_name) VALUES (:site_name)"
        self.execute(sql_query, {"site_name": site_name})

    def _get_site(self, site_name: str) -> List[Dict]:
        sql_query = "SELECT * FROM Sites WHERE site_name = :site_name"
        return self.execute(sql_query, {"site_name": site_name})

    async def async_execute(self, sql_query: str, bind_parameters: Dict) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool_executor, self.execute, sql_query, bind_parameters
        )

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        con = sqlite3.connect(
            self._db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        try:
            with con:  # context manager to commit or rollback transactions
                yield con
        finally:
            con.close()

    def _deploy_db_schema(self) -> None:
        tables = {
            "MachineTypes": [
                "machine_type_id INTEGER PRIMARY KEY AUTOINCREMENT",
                "machine_type VARCHAR(255)",
                "site_id INTEGER",
                "FOREIGN KEY(site_id) REFERENCES Sites(site_id)",
                "CONSTRAINT unique_machine_type_per_site UNIQUE (machine_type, site_id)",  # noqa B950
            ],
            "Resources": [
                "id INTEGER PRIMARY KEY AUTOINCREMENT",
                "remote_resource_uuid VARCHAR(255)",
                "drone_uuid VARCHAR(255) UNIQUE",
                "state_id INTEGER",
                "site_id INTEGER",
                "machine_type_id INTEGER",
                "created TIMESTAMP",
                "updated TIMESTAMP",
                "FOREIGN KEY(state_id) REFERENCES ResourceState(state_id)",
                "FOREIGN KEY(site_id) REFERENCES Sites(site_id)",
                "FOREIGN KEY(machine_type_id) REFERENCES MachineTypes(machine_type_id)",
                "CONSTRAINT unique_remote_resource_uuid_per_site UNIQUE (site_id, remote_resource_uuid)",  # noqa B950
            ],
            "ResourceStates": [
                "state_id INTEGER PRIMARY KEY AUTOINCREMENT",
                "state VARCHAR(255) UNIQUE",
            ],
            "Sites": [
                "site_id INTEGER PRIMARY KEY AUTOINCREMENT",
                "site_name VARCHAR(255) UNIQUE",
            ],
        }

        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA locking_mode = EXCLUSIVE")
            cursor.execute("PRAGMA journal_mode = WAL")
            for table_name, columns in tables.items():
                cursor.execute(
                    f"create table if not exists {table_name} ({', '.join(columns)})"  # noqa b950
                )

            for state in State.get_all_states():
                cursor.execute(
                    "INSERT OR IGNORE INTO ResourceStates(state) VALUES (?)",
                    (state,),
                )

            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_drone_uuid ON Resources (drone_uuid);"  # noqa B950
            )

    async def delete_resource(self, bind_parameters: dict):
        sql_query = """DELETE FROM Resources
        WHERE drone_uuid = :drone_uuid
        AND site_id = (SELECT site_id from Sites WHERE site_name = :site_name)"""
        await self.async_execute(sql_query, bind_parameters)

    def execute(self, sql_query: str, bind_parameters: Dict) -> List[Dict]:
        with self.connect() as connection:
            connection.row_factory = lambda cur, row: {
                col[0]: row[idx] for idx, col in enumerate(cur.description)
            }
            cursor = connection.cursor()
            cursor.execute(sql_query, bind_parameters)
            logger.debug(f"{sql_query},{bind_parameters} executed")
            return cursor.fetchall()

    async def get_resource_state(self, drone_uuid: str):
        sql_query = """
        SELECT RS.state
        FROM Resources R
        JOIN ResourceStates RS ON R.state_id = RS.state_id
        WHERE R.drone_uuid = :drone_uuid
        """
        return await self.async_execute(sql_query, {"drone_uuid": drone_uuid})

    def get_resources(self, site_name: str, machine_type: str) -> List[Dict]:
        sql_query = """
        SELECT R.remote_resource_uuid, R.drone_uuid, RS.state, R.created, R.updated
        FROM Resources R
        JOIN ResourceStates RS ON R.state_id = RS.state_id
        JOIN Sites S ON R.site_id = S.site_id
        JOIN MachineTypes MT ON R.machine_type_id = MT.machine_type_id
        WHERE S.site_name = :site_name AND MT.machine_type = :machine_type"""
        return self.execute(
            sql_query, {"site_name": site_name, "machine_type": machine_type}
        )

    async def insert_resource(self, bind_parameters: Dict) -> None:
        sql_query = """
        INSERT OR ROLLBACK INTO
        Resources(remote_resource_uuid, drone_uuid, state_id, site_id, machine_type_id,
        created, updated)
        SELECT :remote_resource_uuid, :drone_uuid, RS.state_id, S.site_id,
        MT.machine_type_id, :created, :updated
        FROM ResourceStates RS
        JOIN Sites S ON S.site_name = :site_name
        JOIN MachineTypes MT ON MT.machine_type = :machine_type AND MT.site_id =
        S.site_id
        WHERE RS.state = :state"""
        await self.async_execute(sql_query, bind_parameters)

    async def notify(self, state: State, resource_attributes: AttributeDict) -> None:
        state = str(state)
        logger.debug(f"Drone: {str(resource_attributes)} has changed state to {state}")
        bind_parameters = {"state": state}
        bind_parameters.update(resource_attributes)
        await self._dispatch_on_state.get(state, self.update_resource)(bind_parameters)

    async def update_resource(self, bind_parameters: Dict) -> None:
        sql_query = """UPDATE Resources SET updated = :updated,
        remote_resource_uuid = :remote_resource_uuid,
        state_id = (SELECT state_id FROM ResourceStates WHERE state = :state)
        WHERE drone_uuid = :drone_uuid
        AND site_id = (SELECT site_id FROM Sites WHERE site_name = :site_name)"""
        await self.async_execute(sql_query, bind_parameters)
