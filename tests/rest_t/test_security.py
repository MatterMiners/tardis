from tardis.rest import security

from unittest import TestCase
from unittest.mock import patch


class TestSecurity(TestCase):
    mock_config_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_config_patcher = patch("tardis.rest.security.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mock_config_patcher.stop()

    def setUp(self) -> None:
        self.secret_key = (
            "689e7af69a70ad0d97f771371738be00452e81e128a876491c1d373dfbcca949"
        )
        self.algorithm = "HS256"

        config = self.mock_config.return_value
        config.Services.restapi.secret_key = self.secret_key
        config.Services.restapi.algorithm = self.algorithm

    @staticmethod
    def clear_lru_cache():
        security.get_algorithm.cache_clear()
        security.get_secret_key.cache_clear()

    def test_get_secret_key(self):
        self.clear_lru_cache()
        self.assertEqual(security.get_secret_key(), self.secret_key)

    def test_get_algorithm(self):
        self.clear_lru_cache()
        self.assertEqual(security.get_algorithm(), self.algorithm)
