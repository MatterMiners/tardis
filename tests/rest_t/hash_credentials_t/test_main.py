from tardis.rest.hash_credentials.__main__ import hash_credentials, hash_credentials_cli

from unittest import TestCase
from unittest.mock import patch


class TestHashCredentialsMain(TestCase):
    mock_typer_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_typer_patcher = patch("tardis.rest.hash_credentials.__main__.typer")
        cls.mock_typer = cls.mock_typer_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mock_typer_patcher.stop()

    def testHashCredentialsCli(self):
        hash_credentials_cli()
        self.mock_typer.run.assert_called_with(hash_credentials)
