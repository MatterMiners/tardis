from httpx import AsyncClient, ASGITransport

from unittest import TestCase
from unittest.mock import patch

import asyncio


class TestCaseRouters(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_config_patcher = patch("tardis.rest.app.database.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()

        cls.mock_sqlite_registry_patcher = patch(
            "tardis.rest.app.database.SqliteRegistry"
        )
        cls.mock_types_patcher = patch("tardis.rest.app.routers.types.crud")
        cls.mock_crud_patcher = patch("tardis.rest.app.routers.resources.crud")
        cls.mock_sqlite_registry = cls.mock_sqlite_registry_patcher.start()
        cls.mock_types = cls.mock_types_patcher.start()
        cls.mock_crud = cls.mock_crud_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mock_config_patcher.stop()
        cls.mock_sqlite_registry_patcher.stop()
        cls.mock_crud_patcher.stop()
        cls.mock_types_patcher.stop()

    def setUp(self) -> None:
        from tardis.rest.app.main import app

        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )
        config = self.mock_config.return_value
        config.Services.restapi.user_db_url = (
            "sqlite+aiosqlite:///file::memory:?mode=memory&cache=shared&uri=true"
        )

        self._setup_user_db()

    def _setup_user_db(self):
        """Set up in-memory user DB and create test user."""
        from tardis.rest.app.database import (
            get_user_db_engine,
            get_user_session_factory,
        )
        from tardis.rest.app.user_manager import CustomUserManager

        self.test_user = {
            "user_name": "test",
            "password": "test",
            "scopes": ["resources:get", "user:get", "resources:patch"],
        }

        async def _create_test_user():
            from tardis.rest.app.models import Base

            engine = get_user_db_engine()
            async with engine.begin() as conn:
                # Drop and recreate tables to ensure clean state between tests
                # (in-memory DB persists across test runs without this)
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)

            session_factory = get_user_session_factory()
            async with session_factory() as session:
                manager = CustomUserManager(session)
                await manager.create(**self.test_user)

        asyncio.run(_create_test_user())

    def update_scopes(self, scopes: list):
        self.test_user["scopes"] = scopes
        self.login()

    def get_scopes(self):
        return ["resources:get", "user:get", "resources:patch"]

    def login(self, user: dict | None = None):
        response = asyncio.run(
            self.client.post("/user/login", json=user or self.test_user)
        )
        self.assertEqual(response.status_code, 200)
