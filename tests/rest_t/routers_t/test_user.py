from tests.rest_t.routers_t.base_test_case_routers import TestCaseRouters
from tests.utilities.utilities import run_async

# TODO: decrease code repetition by extracting basic auth test into separate function

class TestLogin(TestCaseRouters):
    # Reminder: When defining `setUp`, `setUpClass`, `tearDown` and `tearDownClass`
    # in router tests the corresponding super().function() needs to be called as well.
    def test_login(self):
        # No body and headers
        self.clear_lru_cache()
        response = run_async(self.client.post, "/user/login")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "detail": [
                    {
                        "loc": ["body"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    }
                ]
            },
        )

        # Empty body
        self.clear_lru_cache()
        response = run_async(self.client.post, "/user/login", data="{}")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "detail": [
                    {
                        "loc": ["body", "user_name"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    },
                    {
                        "loc": ["body", "password"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    },
                ]
            },
        )

        self.clear_lru_cache()
        response = run_async(self.client.post, "/user/login", json=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"msg": "Successfully logged in!"},
        )

        self.clear_lru_cache()
        self.config.Services.restapi.get_user.side_effect = lambda user_name: None
        response = run_async(self.client.post, "/user/login", json=self.test_user)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Incorrect username or password"})
        self.config.Services.restapi.get_user.side_effect = None

        self.clear_lru_cache()
        self.login()
        )
        self.login()
        self.assertEqual(response.status_code, 401)
        self.login()
