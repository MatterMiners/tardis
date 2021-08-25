from tardis.rest.service import RestService
from ..utilities.utilities import async_return, run_async

from unittest import TestCase
from unittest.mock import patch


class TestRestService(TestCase):
    def setUp(self) -> None:
        self.algorithm = "test_algorithm"
        self.secret_key = "test_key"
        self.rest_service = RestService(
            algorithm=self.algorithm,
            secret_key=self.secret_key,
        )

    @patch("tardis.rest.service.Server")
    def test_run(self, mocked_server):
        mocked_server().serve.return_value = async_return()

        mocked_server.reset_mock()

        run_async(self.rest_service.run)
        mocked_server.assert_called_with(config=self.rest_service._config)

    def test_secret_key(self):
        self.assertEqual(self.rest_service.secret_key, self.secret_key)

    def test_algorithm(self):
        self.assertEqual(self.rest_service.algorithm, self.algorithm)
        self.assertEqual(RestService(secret_key=self.secret_key).algorithm, "HS256")
