from tardis.rest.app.security import get_algorithm, get_secret_key
from tests.utilities.utilities import run_async

from httpx import AsyncClient

from unittest import TestCase
from unittest.mock import patch


class TestCaseRouters(TestCase):
    mock_sqlite_registry_patcher = None
    mock_crud_patcher = None
    mock_config_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_sqlite_registry_patcher = patch(
            "tardis.rest.app.database.SqliteRegistry"
        )
        cls.mock_crud_patcher = patch("tardis.rest.app.routers.resources.crud")
        cls.mock_config_patcher = patch("tardis.rest.app.security.Configuration")
        cls.mock_sqlite_registry = cls.mock_sqlite_registry_patcher.start()
        cls.mock_crud = cls.mock_crud_patcher.start()
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mock_sqlite_registry_patcher.stop()
        cls.mock_crud_patcher.stop()
        cls.mock_config_patcher.stop()

    def setUp(self) -> None:
        secret_key = "63328dc6b8524bf08b0ba151e287edb498852b77b97f837088de4d17247d032c"
        algorithm = "HS256"

        config = self.mock_config.return_value
        config.Services.restapi.secret_key = secret_key
        config.Services.restapi.algorithm = algorithm

        from tardis.rest.app.main import (
            app,
        )  # has to be imported after SqliteRegistry patch

        self.client = AsyncClient(app=app, base_url="http://test")

    def tearDown(self) -> None:
        run_async(self.client.aclose)

    @staticmethod
    def clear_lru_cache():
        get_algorithm.cache_clear()
        get_secret_key.cache_clear()

    @property
    def headers(
        self,
        token="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0YXJkaXMiLCJzY29wZXMiOlsidXNlcjpyZWFkIl19.l2xDqxEQOLYQq6cDX7RGDcT1XvyupRcBUpvvW1l4yeM",  # noqa B950
    ):
        return {"accept": "application/json", "Authorization": token}
