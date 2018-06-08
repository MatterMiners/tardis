from tardis.utilities.looper import Looper
from unittest import TestCase

import asyncio


class TestLooper(TestCase):
    def setUp(self):
        self.looper1 = Looper()
        self.looper2 = Looper()

    def test_looper_instances(self):
        self.assertNotEqual(id(self.looper1), id(self.looper2))

    def test_get_event_loop(self):
        self.assertEqual(id(self.looper1.get_event_loop()), id(self.looper2.get_event_loop()))

    def test_run_event_loop(self):
        loop = self.looper1.get_event_loop()

        async def test():
            await asyncio.sleep(0.1)
            return

        loop.run_until_complete(test())
