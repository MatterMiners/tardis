from tests.rest_t.routers_t.base_test_case_routers import TestCaseRouters

from datetime import datetime, timedelta, timezone
import asyncio

from jose import jwt


def _replace_user(old_user_name: str, new_user: dict) -> int:
    """Delete a user and create another one, returns the id of the new user"""

    async def _replace():
        from tardis.rest.app.database import get_user_session_factory
        from tardis.rest.app.user_manager import CustomUserManager

        async with get_user_session_factory()() as session:
            manager = CustomUserManager(session)
            await manager.delete(await manager.get_by_username(old_user_name))
            return (await manager.create(**new_user)).id

    return asyncio.run(_replace())


def _set_user_scopes(user_name: str, scopes: list[str]) -> None:
    """Change the scopes assigned to a user in the database"""

    async def _set():
        from tardis.rest.app.database import get_user_session_factory
        from tardis.rest.app.user_manager import CustomUserManager

        async with get_user_session_factory()() as session:
            user = await CustomUserManager(session).get_by_username(user_name)
            user.scopes = scopes
            await session.commit()

    asyncio.run(_set())


def _token(**claims) -> str:
    from tardis.rest.app.user_manager import ALGORITHM, SECRET_KEY

    claims.setdefault("exp", datetime.now(timezone.utc) + timedelta(minutes=5))
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)


class TestUser(TestCaseRouters):
    def test_login(self):
        response = asyncio.run(self.client.post("/user/login"))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "detail": [
                    {
                        "type": "missing",
                        "loc": ["body"],
                        "msg": "Field required",
                        "input": None,
                    }
                ]
            },
        )

        response = asyncio.run(self.client.post("/user/login", json={}))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "detail": [
                    {
                        "type": "missing",
                        "loc": ["body", "user_name"],
                        "msg": "Field required",
                        "input": {},
                    },
                    {
                        "type": "missing",
                        "loc": ["body", "password"],
                        "msg": "Field required",
                        "input": {},
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

    def test_login_password_too_long(self):
        # bcrypt rejects passwords longer than 72 bytes, this must not fail
        for endpoint in ("/user/login", "/user/token"):
            with self.subTest(endpoint=endpoint):
                response = asyncio.run(
                    self.client.post(
                        endpoint, json={"user_name": "test", "password": "a" * 73}
                    )
                )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(
                    response.json(), {"detail": "Incorrect username or password"}
                )

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

    def test_revoked_scope_not_granted_by_existing_token(self):
        response = asyncio.run(self.client.post("/user/token", json=self.test_user))
        self.assertEqual(response.status_code, 200)
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        _set_user_scopes("test", ["resources:get", "resources:patch"])

        response = asyncio.run(self.client.get("/user/me", headers=headers))
        self.assertEqual(response.status_code, 403)

        response = asyncio.run(self.client.get("/user/scopes", headers=headers))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["resources:get", "resources:patch"])

    def test_token_of_deleted_user_not_valid_for_new_user(self):
        response = asyncio.run(self.client.post("/user/token", json=self.test_user))
        self.assertEqual(response.status_code, 200)
        old_token = response.json()["access_token"]

        new_user_id = _replace_user(
            "test",
            {"user_name": "other", "password": "other", "scopes": self.get_scopes()},
        )
        # ids of deleted users must not be reused
        self.assertNotEqual(new_user_id, 1)

        response = asyncio.run(
            self.client.get(
                "/user/scopes", headers={"Authorization": f"Bearer {old_token}"}
            )
        )
        self.assertEqual(response.status_code, 401)

    def test_bearer_scheme_case_insensitive(self):
        response = asyncio.run(self.client.post("/user/token", json=self.test_user))
        self.assertEqual(response.status_code, 200)
        access_token = response.json()["access_token"]

        # The authentication scheme is case-insensitive (RFC 9110, section 11.1)
        for scheme in ("Bearer", "bearer", "BEARER"):
            with self.subTest(scheme=scheme):
                response = asyncio.run(
                    self.client.get(
                        "/user/scopes",
                        headers={"Authorization": f"{scheme} {access_token}"},
                    )
                )
                self.assertEqual(response.status_code, 200)

        for header in ("Bearer", "Bearer ", "Basic dGVzdDp0ZXN0"):
            with self.subTest(header=header):
                response = asyncio.run(
                    self.client.get("/user/scopes", headers={"Authorization": header})
                )
                self.assertEqual(response.status_code, 401)

    def test_access_token_with_other_user_name_rejected(self):
        token = _token(
            sub="1", username="other", scopes=self.get_scopes(), type="access"
        )
        response = asyncio.run(
            self.client.get(
                "/user/scopes", headers={"Authorization": f"Bearer {token}"}
            )
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Not authenticated"})

    def test_refresh_token_with_other_user_name_rejected(self):
        self.client.cookies["tardis_refresh_token"] = _token(
            sub="1", username="other", scopes=self.get_scopes(), type="refresh"
        )
        response = asyncio.run(self.client.post("/user/refresh"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid refresh token"})

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
