from tardis.rest.token_generator.__main__ import generate_token, generate_token_cli

from unittest import TestCase
from unittest.mock import patch


class TestTokenGeneratorMain(TestCase):
    mock_typer_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_typer_patcher = patch("tardis.rest.token_generator.__main__.typer")
        cls.mock_typer = cls.mock_typer_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mock_typer_patcher.stop()

    def testGenerateTokenCli(self):
        generate_token_cli()
        self.mock_typer.run.assert_called_with(generate_token)
