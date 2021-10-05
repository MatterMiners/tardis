from tardis.rest.token_generator.generate_token import generate_token
from tardis.rest.security import get_algorithm, get_secret_key

from typer.testing import CliRunner
from typer import Typer
from unittest import TestCase
from unittest.mock import patch


class TestGenerateToken(TestCase):
    mock_config_patcher = None
    mock_cobald_config_loader_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_config_patcher = patch("tardis.rest.security.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()

        cls.mock_cobald_config_loader_patcher = patch(
            "tardis.rest.token_generator.generate_token.load"
        )
        cls.mock_cobald_config_loader = cls.mock_cobald_config_loader_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mock_config_patcher.stop()
        cls.mock_cobald_config_loader_patcher.stop()

    def setUp(self) -> None:
        self.app = Typer()
        self.app.command()(generate_token)

        self.runner = CliRunner()

        config = self.mock_config.return_value
        config.Services.restapi.secret_key = (
            "752e003f636f402cc23728e185ce8c9eef27b7e02cf509b3015f7757e625b8e4"
        )
        config.Services.restapi.algorithm = "HS256"

    @staticmethod
    def clear_lru_cache():
        get_algorithm.cache_clear()
        get_secret_key.cache_clear()

    def test_generate_token(self):
        result = self.runner.invoke(self.app)
        self.assertNotEqual(result.exit_code, 0)
        self.assertTrue("Missing option '--user-name'" in result.stdout)

        result = self.runner.invoke(self.app, ["--user-name=test"])
        self.assertEqual(result.exit_code, 1)
        self.assertTrue(
            "Either a config-file or a secret-key and algorithm needs to be specified!"
            in result.stdout
        )

        expected_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbInVzZXI6cmVhZCJdfQ.DffmcJT9l3UcwTzjnHS0x3h4XjFALKm5L_ubcF6onMQ"  # noqa: B950

        result = self.runner.invoke(
            self.app,
            [
                "--user-name=test",
                "--algorithm=HS256",
                "--secret-key=752e003f636f402cc23728e185ce8c9eef27b7e02cf509b3015f7757e625b8e4",  # noqa: B950
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout.strip(), expected_token)

        self.clear_lru_cache()

        result = self.runner.invoke(
            self.app, ["--user-name=test", "--config-file=test.yml"]
        )

        self.mock_cobald_config_loader.assert_called_once_with("test.yml")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout.strip(), expected_token)
