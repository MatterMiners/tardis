from tardis.rest.app.models import Base
from tardis.rest.app.user_manager import CustomUserManager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from unittest import TestCase
from unittest.mock import patch

import asyncio
import threading


class TestCustomUserManager(TestCase):
    def run_with_manager(self, test_coroutine):
        """Run a test coroutine with a manager on a fresh in-memory database"""

        async def _run():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            try:
                async with async_sessionmaker(bind=engine)() as session:
                    manager = CustomUserManager(session)
                    await manager.create("test", "test", ["user:get"])
                    return await test_coroutine(manager)
            finally:
                await engine.dispose()

        return asyncio.run(_run())

    def test_authenticate(self):
        async def _test(manager):
            self.assertEqual((await manager.authenticate("test", "test")).id, 1)
            self.assertIsNone(await manager.authenticate("test", "wrong"))

        self.run_with_manager(_test)

    def test_authenticate_unknown_user_checks_password(self):
        # Unknown users take as long as known ones, so that response times do
        # not reveal which user names exist
        async def _test(manager):
            with patch.object(
                CustomUserManager,
                "verify_password",
                wraps=CustomUserManager.verify_password,
            ) as verify_password:
                self.assertIsNone(await manager.authenticate("unknown", "test"))
            verify_password.assert_called_once()

        self.run_with_manager(_test)

    def test_authenticate_does_not_block_event_loop(self):
        threads = []
        verify_password = CustomUserManager.verify_password

        def recording_verify_password(plain_password, hashed_password):
            threads.append(threading.get_ident())
            return verify_password(plain_password, hashed_password)

        async def _test(manager):
            loop_thread = threading.get_ident()
            with patch.object(
                CustomUserManager,
                "verify_password",
                staticmethod(recording_verify_password),
            ):
                await manager.authenticate("test", "test")
            self.assertEqual(len(threads), 1)
            self.assertNotEqual(threads[0], loop_thread)

        self.run_with_manager(_test)
