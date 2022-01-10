import asyncio
import time
import sys
from unittest import TestCase

from tardis.utilities.asyncbulkcall import AsyncBulkCall

from ..utilities.utilities import run_async


class CallCounter:
    def __init__(self, start=0):
        self.calls = start

    async def __call__(self, *tasks):
        this_call = self.calls
        self.calls += 1
        # make *some* runs pause so that this isn't a trivially sequential test
        if this_call % 2:
            await asyncio.sleep(0)
        return [(i, this_call) for i in tasks]


class TestAsyncBulkCall(TestCase):
    @staticmethod
    async def execute(execution: AsyncBulkCall, count: int, delay=None):
        tasks = []
        for i in range(count):
            tasks.append(asyncio.ensure_future(execution(i)))
            if delay is not None:
                await asyncio.sleep(delay)
        return await asyncio.gather(*tasks)

    def test_bulk_size(self):
        """Test that bulks are formed by size"""
        for size in (1, 10, 100, 1000, 2, 3, 5, 7, 97, 2129):
            with self.subTest(size=size):
                execution = AsyncBulkCall(CallCounter(), size=size, delay=0.1)
                result = run_async(self.execute, execution, count=size * 3 + 5)
                self.assertEqual(result, [(i, i // size) for i in range(size * 3 + 5)])

    def test_bulk_delay(self):
        """Test that bulks are formed by delay"""
        # check that delay forces a bulk if the size is too large
        bulk_delay = 0.05
        execution = AsyncBulkCall(CallCounter(), size=2 ** 32, delay=bulk_delay)
        before = time.monotonic()
        result = run_async(self.execute, execution, count=2048)
        after = time.monotonic()
        self.assertLess(after - before, bulk_delay * 4)
        self.assertEqual(result, [(i, 0) for i in range(2048)])

    def test_delay_tiny(self):
        """Test that a tiny delay cannot stall execution"""
        # sys.float_info.min is not the smallest float possible,
        # but it should be insignificant in all math
        execution = AsyncBulkCall(CallCounter(), size=2 ** 32, delay=sys.float_info.min)
        result = run_async(self.execute, execution, count=2048)
        self.assertEqual(result, [(i, i) for i in range(2048)])

    def test_sanity_checks(self):
        """Test against illegal settings"""
        for wrong_size in (0, -1, 0.5, 2j, "15"):
            with self.subTest(size=wrong_size):
                with self.assertRaises(ValueError):
                    AsyncBulkCall(CallCounter(), size=wrong_size, delay=1.0)
        for wrong_delay in (0, -5, 17j, "10"):
            with self.subTest(delay=wrong_delay):
                with self.assertRaises((ValueError, TypeError)):
                    AsyncBulkCall(CallCounter(), size=100, delay=wrong_delay)
        for wrong_concurrency in (0, 2.3, -5, 17j, "10"):
            with self.subTest(delay=wrong_concurrency):
                with self.assertRaises(ValueError):
                    AsyncBulkCall(
                        CallCounter(),
                        size=100,
                        delay=1.0,
                        concurrent=wrong_concurrency,
                    )
