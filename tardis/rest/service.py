from cobald.daemon import service

from uvicorn.config import Config
from uvicorn.server import Server

from functools import lru_cache
import asyncio


@service(flavour=asyncio)
class RestService(object):
    def __init__(self, secret_key: str, algorithm: str = "HS256", **fast_api_args):
        self._algorithm = algorithm
        self._secret_key = secret_key

        # necessary to avoid that the TARDIS' logger configuration is overwritten!
        if "log_config" not in fast_api_args:
            fast_api_args["log_config"] = None
        self._config = Config("tardis.rest.app:app", **fast_api_args)

    @property
    @lru_cache(maxsize=16)
    def algorithm(self) -> str:
        return self._algorithm

    @property
    @lru_cache(maxsize=16)
    def secret_key(self) -> str:
        return self._secret_key

    async def run(self) -> None:
        await Server(config=self._config).serve()
