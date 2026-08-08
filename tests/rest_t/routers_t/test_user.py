from tests.rest_t.routers_t.base_test_case_routers import TestCaseRouters

import asyncio


class TestUser(TestCaseRouters):
    def test_login(self):
        response = asyncio.run(self.client.post("/user/login"))
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

        response = asyncio.run(self.client.post("/user/login", data="{}"))
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

        response = asyncio.run(self.client.post("/user/login", json=self.test_user))
        self.assertEqual(response.status_code, 200)
        self.assertIn("tardis_access_token", response.cookies)
        self.assertIn("tardis_refresh_token", response.cookies)

    def test_login_wrong_password(self):
        self.test_user["password"] = "wrong"
        response = asyncio.run(self.client.post("/user/login", json=self.test_user))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Incorrect username or password"})

    def test_logout(self):
        response = asyncio.run(self.client.post("/user/logout"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Not authenticated"})

        self.login()
        response = asyncio.run(self.client.post("/user/logout"))
        self.assertEqual(response.status_code, 200)

        # prevent second logout
        response = asyncio.run(self.client.post("/user/logout"))
        self.assertEqual(response.status_code, 401)

    def test_refresh(self):
        # not logged in yet
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Missing refresh token"})

        self.login()
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 200)

        # invalid access token but valid refresh token
        self.client.cookies["access_token_cookie"] = "invalid"
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 200)

    def test_user_me(self):
        # Not logged in yet
        response = asyncio.run(self.client.get("/user/me"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Not authenticated"})

        self.login()
        response = asyncio.run(self.client.get("/user/me"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"user_name": "test", "scopes": self.get_scopes()},
        )

        # missing scope
        self.update_scopes(["resources:get"])
        self.login()
        response = asyncio.run(self.client.get("/user/me"))
        self.assertEqual(response.status_code, 403)

    def test_get_token_scopes(self):
        self.login(
            {
                "user_name": "test",
                "password": "test",
                "scopes": ["resources:get"],
            }
        )
        response = asyncio.run(self.client.get("/user/scopes"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["resources:get"])
