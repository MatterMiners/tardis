from tardis.rest.app.database import get_sql_registry

from unittest import TestCase
from unittest.mock import patch


class TestDatabase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch("tardis.rest.app.database.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mock_config_patcher.stop()

    def setUp(self) -> None:
        # Necessary since user_db_url is used in the RestService constructor and
        # is read from the Configuration singleton.
        config = self.mock_config.return_value
        config.Services.restapi.user_db_url = (
            "sqlite+aiosqlite:///file::memory:?cache=shared"
        )

    @patch("tardis.rest.app.database.SqliteRegistry")
    def test_get_sql_registry(self, mocked_sqlite_registry):
        self.assertEqual(get_sql_registry()(), mocked_sqlite_registry())
