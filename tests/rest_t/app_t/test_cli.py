import pathlib
import tempfile
from unittest import TestCase

from typer.testing import CliRunner

from tardis.rest.app.cli import app as cli_app


class TestCLI(TestCase):
    runner = CliRunner()

    def setUp(self):
        """Creates a fresh, isolated temporary database file for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = pathlib.Path(self.temp_dir.name) / "test.db"
        # .as_posix() ensures the path is formatted correctly for SQLAlchemy URLs on all OSs  # noqa: B950
        self.db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    def tearDown(self):
        """Cleans up the temporary database file after each test."""
        self.temp_dir.cleanup()

    def test_get_user_session_creates_tables(self):
        result = self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "list-users",
            ],
        )
        self.assertEqual(result.exit_code, 0)

    def test_add_user_success_with_scopes(self):
        result = self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "add",
                "--username",
                "testuser1",
                "--password",
                "testpass1",
                "--scopes",
                "resources:get,user:get,resources:patch",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("created successfully", result.stdout)

        list_result = self.runner.invoke(
            cli_app, ["--user-db-url", self.db_url, "list-users"]
        )
        self.assertEqual(list_result.exit_code, 0)
        self.assertIn("testuser1", list_result.stdout)
        self.assertIn("resources:get", list_result.stdout)
        self.assertIn("user:get", list_result.stdout)
        self.assertIn("resources:patch", list_result.stdout)

    def test_add_user_success_without_scopes(self):
        result = self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "add",
                "--username",
                "testuser2",
                "--password",
                "testpass2",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("created successfully", result.stdout)

        list_result = self.runner.invoke(
            cli_app, ["--user-db-url", self.db_url, "list-users"]
        )
        self.assertEqual(list_result.exit_code, 0)
        self.assertIn("testuser2", list_result.stdout)
        self.assertIn("none", list_result.stdout)

    def test_add_user_whitespace_in_scopes(self):
        result = self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "add",
                "--username",
                "testuser3",
                "--password",
                "testpass3",
                "--scopes",
                "a, b, c",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("created successfully", result.stdout)
        self.assertIn("['a', 'b', 'c']", result.stdout)

        list_result = self.runner.invoke(
            cli_app, ["--user-db-url", self.db_url, "list-users"]
        )
        self.assertEqual(list_result.exit_code, 0)
        self.assertIn("testuser3", list_result.stdout)
        self.assertIn("a, b, c", list_result.stdout)

    def test_add_user_duplicate_returns_error(self):
        self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "add",
                "--username",
                "duplicate_user",
                "--password",
                "password123",
            ],
        )
        result = self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "add",
                "--username",
                "duplicate_user",
                "--password",
                "password456",
            ],
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error creating user", result.stderr)

    def test_list_users_success(self):
        self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "add",
                "--username",
                "listuser1",
                "--password",
                "pass1",
                "--scopes",
                "resources:get",
            ],
        )
        self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "add",
                "--username",
                "listuser2",
                "--password",
                "pass2",
            ],
        )
        result = self.runner.invoke(
            cli_app, ["--user-db-url", self.db_url, "list-users"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("listuser1", result.stdout)
        self.assertIn("listuser2", result.stdout)

    def test_list_users_empty(self):
        result = self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "list-users",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No users found.", result.stdout)

    def test_delete_user_success(self):
        self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "add",
                "--username",
                "deleteuser",
                "--password",
                "deletepass",
            ],
        )
        result = self.runner.invoke(
            cli_app,
            ["--user-db-url", self.db_url, "delete", "--username", "deleteuser"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("deleted successfully", result.stdout)

        list_result = self.runner.invoke(
            cli_app, ["--user-db-url", self.db_url, "list-users"]
        )
        self.assertEqual(list_result.exit_code, 0)
        self.assertNotIn("deleteuser", list_result.stdout)

    def test_delete_user_not_found(self):
        result = self.runner.invoke(
            cli_app,
            [
                "--user-db-url",
                self.db_url,
                "delete",
                "--username",
                "nonexistent_user",
            ],
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not found", result.stderr)
