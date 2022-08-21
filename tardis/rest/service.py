from .app.security import DatabaseUser, LoginUser
from .app.userdb import UserDB
from cobald.daemon import service
from cobald.daemon.plugins import yaml_tag
import threading

from uvicorn.config import Config
from uvicorn.server import Server

from functools import lru_cache
from typing import Optional
import asyncio


@service(flavour=asyncio)
@yaml_tag(eager=True)
class RestService(object):
    def __init__(
        self,
        user_db_file: str = "users.db",
        **fast_api_args,
    ):
        self._db = UserDB(user_db_file)
        # if table already exists, ignore
        self._db.try_create_users()

        # necessary to avoid that the TARDIS' logger configuration is overwritten!
        if "log_config" not in fast_api_args:
            fast_api_args["log_config"] = None

        self._config = Config("tardis.rest.app.main:app", **fast_api_args)

    @lru_cache(maxsize=16)
    def get_user(self, user_name: str) -> Optional[DatabaseUser]:
        try:
            return self._db.get_user(user_name)
        except:
            return None

    def add_user(self, user: DatabaseUser):
        self._db.add_user(user)

    async def run(self) -> None:
        server = Server(config=self._config)
        await server.serve()
        # See https://github.com/encode/uvicorn/issues/1579
        # The server has shut down after receiving *and suppressing* a signal.
        # Explicitly raise the corresponding shutdown exception as a workaround.
        if server.should_exit and threading.current_thread() is threading.main_thread():
            raise KeyboardInterrupt
