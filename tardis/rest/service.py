from cobald.daemon import service

from uvicorn.config import Config
from uvicorn.server import Server

from functools import lru_cache
import asyncio


@service(flavour=asyncio)
class RestService(object):
    def __init__(self, secret_key, algorithm="HS256", **fast_api_args):
        self._algorithm = algorithm
        self._secret_key = secret_key
        self._config = Config("tardis.rest.app:app", **fast_api_args)

    @property
    @lru_cache(maxsize=16)
    def algorithm(self):
        return self._algorithm

    @property
    @lru_cache(maxsize=16)
    def secret_key(self):
        return self._secret_key

    async def run(self):
        await Server(config=self._config).serve()
