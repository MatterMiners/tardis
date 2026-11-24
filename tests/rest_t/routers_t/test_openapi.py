from tests.rest_t.routers_t.base_test_case_routers import TestCaseRouters

import asyncio


class TestOpenAPI(TestCaseRouters):
    def get_openapi(self) -> dict:
        response = asyncio.run(self.client.get("/openapi.json"))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_security_schemes(self):
        schemes = self.get_openapi()["components"]["securitySchemes"]
        self.assertEqual(len(schemes), 2)

        bearer, cookie = (
            next(scheme for scheme in schemes.values() if scheme["type"] == kind)
            for kind in ("http", "apiKey")
        )
        self.assertEqual(bearer["scheme"], "bearer")
        self.assertEqual(bearer["bearerFormat"], "JWT")
        self.assertEqual(cookie["in"], "cookie")
        self.assertEqual(cookie["name"], "tardis_access_token")

    def test_protected_endpoints_declare_security(self):
        paths = self.get_openapi()["paths"]
        for path, method in (
            ("/resources/", "get"),
            ("/resources/{drone_uuid}/drain", "patch"),
            ("/types/states", "get"),
            ("/user/me", "get"),
            ("/user/scopes", "get"),
            ("/user/logout", "post"),
        ):
            with self.subTest(endpoint=f"{method.upper()} {path}"):
                self.assertTrue(paths[path][method].get("security"))

        for path in ("/user/login", "/user/token", "/user/refresh"):
            with self.subTest(endpoint=f"POST {path}"):
                self.assertFalse(paths[path]["post"].get("security"))
