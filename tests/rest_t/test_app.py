from ..utilities.utilities import async_return, run_async

from httpx import AsyncClient

from unittest import TestCase
from unittest.mock import patch


class TestApp(TestCase):
    mock_sqlite_registry_patcher = None
    mock_crud_patcher = None
    mock_config_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_sqlite_registry_patcher = patch("tardis.rest.database.SqliteRegistry")
        cls.mock_crud_patcher = patch("tardis.rest.crud")
        cls.mock_config_patcher = patch("tardis.rest.security.Configuration")
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

        from tardis.rest.app import app  # has to be imported after SqliteRegistry patch

        self.client = AsyncClient(app=app, base_url="http://test")

    def tearDown(self) -> None:
        run_async(self.client.aclose)

    @property
    def headers(self):
        token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0YXJkaXMiLCJzY29wZXMiOlsidXNlcjpyZWFkIl19.l2xDqxEQOLYQq6cDX7RGDcT1XvyupRcBUpvvW1l4yeM"  # noqa B950

        return {"accept": "application/json", "Authorization": token}

    def test_get_state(self):
        self.mock_crud.get_resource_state.return_value = async_return(
            return_value=[{"drone_uuid": "test-0123456789", "state": "AvailableState"}]
        )

        response = run_async(
            self.client.get, "/state/test-0123456789", headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"drone_uuid": "test-0123456789", "state": "AvailableState"},
        )

        self.mock_crud.get_resource_state.return_value = async_return(return_value=[])
        response = run_async(
            self.client.get, "/state/test-1234567890", headers=self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Drone not found"})

        response = run_async(
            self.client.get, "/state/test-invalid", headers=self.headers
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "detail": [
                    {
                        "ctx": {"pattern": "^\\S+-[A-Fa-f0-9]{10}$"},
                        "loc": ["path", "drone_uuid"],
                        "msg": 'string does not match regex "^\\S+-[A-Fa-f0-9]{10}$"',
                        "type": "value_error.str.regex",
                    }
                ]
            },
        )

        response = run_async(self.client.get, "/state", headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not Found"})