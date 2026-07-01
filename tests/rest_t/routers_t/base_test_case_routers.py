from tests.utilities.utilities import run_async

from httpx import AsyncClient, ASGITransport

from unittest import TestCase
from unittest.mock import patch, AsyncMock


class TestCaseRouters(TestCase):
    mock_sqlite_registry_patcher = None
    mock_crud_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
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
        cls.mock_sqlite_registry_patcher.stop()
        cls.mock_crud_patcher.stop()

    def setUp(self) -> None:
        from tardis.rest.app.main import (
            app,
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )
        self.test_user = {
            "user_name": "test",
            "password": "test",
            "scopes": ["resources:get", "user:get"],
        }
        self._mock_user_db()

    def _mock_user_db(self):
        from tardis.rest.app.models import User

        mock_user = User(
            id=1,
            user_name="test",
            hashed_password="$2b$12$Gkl8KYNGRMhx4kB0bKJnyuRuzOrx3LZlWf1CReIsDk9HyWoUGBihG",
            scopes=["resources:get", "user:get", "resources:patch"],
        )

        async def mock_get_user_db():
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_user)
            yield mock_db

        self.user_db_patcher = patch("tardis.rest.app.routers.user.get_user_db", mock_get_user_db)
        self.user_db_patcher.start()

    def set_scopes(self, scopes: list):
        pass

    def reset_scopes(self):
        pass

    def get_scopes(self):
        return ["resources:get", "user:get", "resources:patch"]

    def tearDown(self) -> None:
        run_async(self.client.aclose)
        self.user_db_patcher.stop()

    def login(self, user: dict = None):
        response = run_async(
            self.client.post, "/user/login", json=user or self.test_user
        )
        self.assertEqual(response.status_code, 200)