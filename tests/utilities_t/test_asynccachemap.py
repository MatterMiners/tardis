from tardis.utilities.asynccachemap import AsyncCacheMap

from json.decoder import JSONDecodeError
from unittest import TestCase
import asyncio


class TestAsyncCacheMap(TestCase):
    def setUp(self):
        self.test_data = {'testA': 123, 'testB': 'Random String'}
        self.async_cache_map = AsyncCacheMap(update_coroutine=self.update_function)
        self.failing_async_cache_map = AsyncCacheMap(update_coroutine=self.failing_update_function)

    async def failing_update_function(self):
        raise JSONDecodeError(msg='Bla', doc='Blubb', pos=99)

    async def update_function(self):
        return self.test_data

    def update_status(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_cache_map.update_status())

    def test_update_async_cache_map(self):
        self.update_status()

    def test_len_async_cache_map(self):
        self.update_status()
        self.assertEqual(len(self.async_cache_map), len(self.test_data))

    def test_get_async_cache_map(self):
        self.update_status()
        self.assertEqual(self.async_cache_map.get('testA'), self.test_data.get('testA'))
        self.assertEqual(self.async_cache_map['testB'], self.test_data['testB'])

    def test_iter_async_cache_map(self):
        self.update_status()

        for key, value in self.async_cache_map.items():
            self.assertEqual(value, self.test_data.get(key))

    def test_failing_update(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.failing_async_cache_map.update_status())
        self.assertEqual(len(self.failing_async_cache_map), 0)
