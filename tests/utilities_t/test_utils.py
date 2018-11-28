from tardis.utilities.utils import async_run_command
from tardis.exceptions.tardisexceptions import AsyncRunCommandFailure

from unittest import TestCase
import asyncio


class TestAsyncRunCommand(TestCase):
    def test_async_run_command(self):
        loop = asyncio.get_event_loop()

        loop.run_until_complete(async_run_command('exit 0'))
        loop.run_until_complete(async_run_command('exit 255'))

        with self.assertRaises(AsyncRunCommandFailure):
            loop.run_until_complete(async_run_command('exit 1'))

        self.assertEqual(loop.run_until_complete(async_run_command('echo "Test"')), "Test")
