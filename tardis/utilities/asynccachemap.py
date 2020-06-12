from ..exceptions.executorexceptions import CommandExecutionFailure
from collections.abc import Mapping
from datetime import datetime
from datetime import timedelta

import asyncio
import logging
import json

logger = logging.getLogger("cobald.runtime.tardis.utilities.asynccachemap")


class AsyncCacheMap(Mapping):
    def __init__(self, update_coroutine, max_age: int = 60 * 15):
        self._update_coroutine = update_coroutine
        self._max_age = max_age
        self._last_update = datetime.fromtimestamp(0)
        self._data = {}
        self._lock = None

    @property
    def _async_lock(self):
        # Create lock once tardis event loop is running.
        # To avoid got Future <Future pending> attached to a different loop exception
        if not self._lock:
            self._lock = asyncio.Lock()
        return self._lock

    @property
    def last_update(self) -> datetime:
        return self._last_update

    async def update_status(self) -> None:
        current_time = datetime.now()

        async with self._async_lock:
            if (current_time - self._last_update) > timedelta(seconds=self._max_age):
                try:
                    data = await self._update_coroutine()
                except json.decoder.JSONDecodeError as je:
                    logger.warning(
                        f"AsyncMap update_status failed: Could not decode json {je}"
                    )
                except CommandExecutionFailure as cf:
                    logger.warning(f"AsyncMap update_status failed: {cf}")
                else:
                    self._data = data
                    self._last_update = current_time

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, item):
        return self._data[item]

    def __len__(self):
        return len(self._data)
