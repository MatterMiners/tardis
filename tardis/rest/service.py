from cobald.daemon import service
from cobald.daemon.plugins import yaml_tag
import threading

from uvicorn.config import Config
from uvicorn.server import Server

import asyncio


@service(flavour=asyncio)
@yaml_tag(eager=True)
class RestService(object):
    def __init__(
        self,
        user_db_url: str = "sqlite+aiosqlite:///./users.db",
        **fast_api_args,
    ):
        if "log_config" not in fast_api_args:
            fast_api_args["log_config"] = None

        self._config = Config("tardis.rest.app.main:app", **fast_api_args)

        from tardis.rest.app import database
        database.user_db_url = user_db_url

    async def run(self) -> None:
        server = Server(config=self._config)
        await server.serve()
        # See https://github.com/encode/uvicorn/issues/1579
        # The server has shut down after receiving *and suppressing* a signal.
        # Explicitly raise the corresponding shutdown exception as a workaround.
        if server.should_exit and threading.current_thread() is threading.main_thread():
            raise KeyboardInterrupt
