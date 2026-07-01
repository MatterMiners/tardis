from tests.rest_t.routers_t.base_test_case_routers import TestCaseRouters
from tests.utilities.utilities import run_async


class TestUser(TestCaseRouters):
    def test_login(self):
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

        response = run_async(self.client.post, "/user/login", json=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())
        self.assertEqual(response.json()["token_type"], "bearer")

    def test_login_wrong_password(self):
        self.test_user["password"] = "wrong"
        response = run_async(self.client.post, "/user/login", json=self.test_user)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Incorrect username or password"})

    def test_logout(self):
        response = run_async(self.client.post, "/user/logout")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Not authenticated"}
        )

        self.login()
        response = run_async(self.client.post, "/user/logout")
        self.assertEqual(response.status_code, 200)

        response = run_async(self.client.post, "/user/logout")
        self.assertEqual(response.status_code, 401)

    def test_refresh(self):
        response = run_async(self.client.post, "/user/refresh")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Missing refresh token"}
        )

        self.login()
        response = run_async(self.client.post, "/user/refresh")
        self.assertEqual(response.status_code, 200)

    def test_user_me(self):
        response = run_async(self.client.get, "/user/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Not authenticated"}
        )

        self.login()
        response = run_async(self.client.get, "/user/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"user_name": "test", "scopes": self.get_scopes()},
        )

    def test_get_token_scopes(self):
        self.login(
            {
                "user_name": "test",
                "password": "test",
                "scopes": ["resources:get"],
            }
        )
        response = run_async(self.client.get, "/user/token_scopes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["resources:get"])