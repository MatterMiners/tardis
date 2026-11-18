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

    def test_logout_cookie_attributes(self):
        from tardis.rest.app.routers import user as user_module

        self.login()
        # Emulate production mode, cookies were set before in development mode
        user_module._SECURE_COOKIE = True

        response = asyncio.run(self.client.post("/user/logout"))
        self.assertEqual(response.status_code, 200)

        set_cookies = response.headers.get_list("set-cookie")
        self.assertEqual(len(set_cookies), 2)
        for name, header in zip(
            ("tardis_access_token", "tardis_refresh_token"), set_cookies, strict=True
        ):
            with self.subTest(cookie=name):
                self.assertTrue(header.startswith(f"{name}="))
                self.assertIn("HttpOnly", header)
                self.assertIn("Secure", header)
                self.assertIn("SameSite=lax", header)

    def test_refresh(self):
        # not logged in yet
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Missing refresh token"})

        self.login()
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 200)

        # invalid access token but valid refresh token
        self.client.cookies["tardis_access_token"] = "invalid"
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 200)

    def test_refresh_invalid_token(self):
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        from tardis.rest.app.user_manager import ALGORITHM, SECRET_KEY

        expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
        invalid_tokens = {
            "malformed": "garbage",
            "wrong_signature": jwt.encode(
                {"sub": "1", "scopes": [], "exp": expiry},
                "wrong-key",
                algorithm=ALGORITHM,
            ),
            "expired": jwt.encode(
                {
                    "sub": "1",
                    "scopes": [],
                    "type": "refresh",
                    "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
                },
                SECRET_KEY,
                algorithm=ALGORITHM,
            ),
            "missing_sub": jwt.encode(
                {"scopes": [], "type": "refresh", "exp": expiry},
                SECRET_KEY,
                algorithm=ALGORITHM,
            ),
            "non_integer_sub": jwt.encode(
                {"sub": "abc", "scopes": [], "type": "refresh", "exp": expiry},
                SECRET_KEY,
                algorithm=ALGORITHM,
            ),
            "missing_type": jwt.encode(
                {"sub": "1", "scopes": [], "exp": expiry},
                SECRET_KEY,
                algorithm=ALGORITHM,
            ),
        }

        for name, token in invalid_tokens.items():
            with self.subTest(token=name):
                self.client.cookies["tardis_refresh_token"] = token
                response = asyncio.run(self.client.post("/user/refresh"))
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Invalid refresh token"})

    def test_refresh_token_rejected_as_access_token(self):
        response = asyncio.run(self.client.post("/user/login", json=self.test_user))
        self.assertEqual(response.status_code, 200)
        refresh_token = response.cookies["tardis_refresh_token"]

        response = asyncio.run(
            self.client.get(
                "/user/me", headers={"Authorization": f"Bearer {refresh_token}"}
            )
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Not authenticated"})

    def test_access_token_rejected_as_refresh_token(self):
        response = asyncio.run(self.client.post("/user/token", json=self.test_user))
        self.assertEqual(response.status_code, 200)
        access_token = response.json()["access_token"]

        self.client.cookies["tardis_refresh_token"] = access_token
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid refresh token"})

    def test_login_empty_scopes(self):
        self.login({"user_name": "test", "password": "test", "scopes": []})

        response = asyncio.run(self.client.get("/user/scopes"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        response = asyncio.run(self.client.get("/user/me"))
        self.assertEqual(response.status_code, 403)

    def test_token_empty_scopes(self):
        response = asyncio.run(
            self.client.post(
                "/user/token",
                json={"user_name": "test", "password": "test", "scopes": []},
            )
        )
        self.assertEqual(response.status_code, 200)
        access_token = response.json()["access_token"]

        response = asyncio.run(
            self.client.get(
                "/user/scopes", headers={"Authorization": f"Bearer {access_token}"}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_refresh_keeps_requested_scopes(self):
        self.login(
            {
                "user_name": "test",
                "password": "test",
                "scopes": ["resources:get"],
            }
        )
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 200)

        response = asyncio.run(self.client.get("/user/scopes"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["resources:get"])

        # user:get was not requested at login and must not be granted by refresh
        response = asyncio.run(self.client.get("/user/me"))
        self.assertEqual(response.status_code, 403)

    def test_refresh_revoked_scope(self):
        # Login with full scopes (refresh token gets all 3 scopes)
        self.login()

        # Revoke "user:get" from the user directly in the DB
        async def _revoke_scope():
            from tardis.rest.app.database import get_user_session_factory
            from tardis.rest.app.models import User
            from sqlalchemy import select

            session_factory = get_user_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(User).where(User.user_name == "test")
                )
                user = result.scalar_one_or_none()
                user.scopes = ["resources:get", "resources:patch"]
                await session.commit()

        asyncio.run(_revoke_scope())

        # Refresh should fail — refresh token still has "user:get"
        # but the user's DB scopes no longer include it
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 403)

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
