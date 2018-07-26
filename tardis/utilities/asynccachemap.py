from ..utilities.looper import Looper
from collections.abc import Mapping
from time import time
import asyncio


class AsyncCacheMap(Mapping):
    def __init__(self, update_coroutine, max_age: int= 60 * 15):
        self._update_coroutine = update_coroutine
        self._max_age = max_age
        self._last_update = 0
        self._data = {}
        Looper().get_event_loop().create_task(self._update_status())

    async def _update_status(self):
        while True:
            self._data = await self._update_coroutine()
            self._last_update = time()
            await asyncio.sleep(self._max_age)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, item):
        return self._data[item]

    def __len__(self):
        return len(self._data)
