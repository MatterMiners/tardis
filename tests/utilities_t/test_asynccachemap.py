from tardis.exceptions.executorexceptions import CommandExecutionFailure
from tardis.utilities.asynccachemap import AsyncCacheMap

from ..utilities.utilities import run_async

from json.decoder import JSONDecodeError
from datetime import datetime
from datetime import timedelta
from unittest import TestCase

import logging


class TestAsyncCacheMap(TestCase):
    def setUp(self):
        self.test_data = {"testA": 123, "testB": "Random String"}
        self.async_cache_map = AsyncCacheMap(update_coroutine=self.update_function)
        self.json_failing_async_cache_map = AsyncCacheMap(
            update_coroutine=self.json_failing_update_function
        )
        self.command_failing_async_cache_map = AsyncCacheMap(
            update_coroutine=self.command_failing_update_function
        )

    async def json_failing_update_function(self):
        raise JSONDecodeError(msg="Bla", doc="Blubb", pos=99)

    async def command_failing_update_function(self):
        raise CommandExecutionFailure(
            message="Failure", stdout="Failure", stderr="Failure", exit_code=2
        )

    async def update_function(self):
        return self.test_data

    def update_status(self):
        run_async(self.async_cache_map.update_status)

    def test_update_async_cache_map(self):
        self.update_status()

    def test_len_async_cache_map(self):
        self.update_status()
        self.assertEqual(len(self.async_cache_map), len(self.test_data))

    def test_get_async_cache_map(self):
        self.update_status()
        self.assertEqual(self.async_cache_map.get("testA"), self.test_data.get("testA"))
        self.assertEqual(self.async_cache_map["testB"], self.test_data["testB"])

    def test_iter_async_cache_map(self):
        self.update_status()

        for key, value in self.async_cache_map.items():
            self.assertEqual(value, self.test_data.get(key))

    def test_json_failing_update(self):
        with self.assertLogs(level=logging.WARNING):
            run_async(self.json_failing_async_cache_map.update_status)
            self.assertEqual(len(self.json_failing_async_cache_map), 0)

    def test_command_failing_update(self):
        with self.assertLogs(level=logging.WARNING):
            run_async(self.json_failing_async_cache_map.update_status)
            self.assertEqual(len(self.json_failing_async_cache_map), 0)

    def test_last_update(self):
        self.assertEqual(self.async_cache_map.last_update, datetime.fromtimestamp(0))
        run_async(self.async_cache_map.update_status)
        self.assertTrue(
            datetime.now() - self.async_cache_map.last_update < timedelta(seconds=1)
        )
