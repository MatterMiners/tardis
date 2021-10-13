from .app.security import UserCredentials
from cobald.daemon import service

from uvicorn.config import Config
from uvicorn.server import Server

from functools import lru_cache
from typing import List
import asyncio


@service(flavour=asyncio)
class RestService(object):
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        users: List = None,
        **fast_api_args,
    ):
        self._algorithm = algorithm
        self._secret_key = secret_key
        self._users = users or []

        # necessary to avoid that the TARDIS' logger configuration is overwritten!
        if "log_config" not in fast_api_args:
            fast_api_args["log_config"] = None
        self._config = Config("tardis.rest.app.main:app", **fast_api_args)

    @property
    @lru_cache(maxsize=16)
    def algorithm(self) -> str:
        return self._algorithm

    @property
    @lru_cache(maxsize=16)
    def secret_key(self) -> str:
        return self._secret_key

    @lru_cache(maxsize=16)
    def get_user(self, user_name: str) -> [None, UserCredentials]:
        for user in self._users:
            if user["user_name"] == user_name:
                return UserCredentials(**user)
        return None

    async def run(self) -> None:
        await Server(config=self._config).serve()
