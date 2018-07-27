from collections.abc import Mapping
from time import time


class AsyncCacheMap(Mapping):
    def __init__(self, update_coroutine, max_age: int= 60 * 15):
        self._update_coroutine = update_coroutine
        self._max_age = max_age
        self._last_update = 0
        self._data = {}

    async def update_status(self):
        current_time = time()
        if (current_time - self._last_update) > self._max_age:
            self._data = await self._update_coroutine()
            self._last_update = current_time

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, item):
        return self._data[item]

    def __len__(self):
        return len(self._data)
