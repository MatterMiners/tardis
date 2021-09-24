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
            "63328dc6b8524bf08b0ba151e287edb498852b77b97f837088de4d17247d032c"
        )
        self.algorithm = "HS256"

        config = self.mock_config.return_value
        config.Services.restapi.secret_key = self.secret_key
        config.Services.restapi.algorithm = self.algorithm

    def test_get_secret_key(self):
        self.assertEqual(security.get_secret_key(), self.secret_key)

    def test_get_algorithm(self):
        self.assertEqual(security.get_algorithm(), self.algorithm)
