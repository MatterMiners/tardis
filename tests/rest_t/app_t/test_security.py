from tardis.exceptions.tardisexceptions import TardisError
from tardis.rest.app.security import (
    check_authentication,
    check_scope_permissions,
    get_user,
    hash_password,
)
from tardis.utilities.attributedict import AttributeDict

from fastapi import HTTPException, status


from unittest import TestCase
from unittest.mock import patch


class TestSecurity(TestCase):
    mock_config_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_config_patcher = patch("tardis.rest.app.security.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mock_config_patcher.stop()

    def setUp(self) -> None:
        self.algorithm = "HS256"

        self.infinite_resources_get_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbInJlc291cmNlczpnZXQiXX0.FTzUlLfPgb2WXFUSPSoUsvqHI67QtSO2Boash_6eVBg"  # noqa B950
        self.limited_resources_get_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbInJlc291cmNlczpnZXQiXSwiZXhwIjo5MDB9.nN4wmo7S5wHq3LcnYTL0J2Z1wIqBCPOHkOe_lSBmDS0"  # noqa B950
        self.infinite_resources_get_update_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbInJlc291cmNlczpnZXQiLCJyZXNvdXJjZXM6cHV0Il19.KzwdGOo8mp90MlkdcBr_3eZ4KxH35Vi-Eu_hTFGFOWU"  # noqa B950

        def mocked_get_user(user_name):
            if user_name == "test":
                return AttributeDict(
                    user_name="test",
                    hashed_password="$2b$12$Gkl8KYNGRMhx4kB0bKJnyuRuzOrx3LZlWf1CReIsDk9HyWoUGBihG",  # noqa B509
                    scopes=["resources:get"],
                )
            return None

        config = self.mock_config.return_value
        config.Services.restapi.algorithm = self.algorithm
        config.Services.restapi.get_user.side_effect = mocked_get_user

    @staticmethod
    def clear_lru_cache():
        get_user.cache_clear()

    def test_check_scope_permissions(self):
        with self.assertRaises(HTTPException) as cm:
            check_scope_permissions(
                ["user:get", "resources:get"], ["user:get", "user:put"]
            )
        self.assertEqual(cm.exception.status_code, status.HTTP_403_FORBIDDEN)
        self.assertDictEqual(
            cm.exception.detail,
            {
                "msg": "Not enough permissions",
                "failedAt": "resources:get",
                "allowedScopes": ["user:get", "user:put"],
            },
        )
        check_scope_permissions(["resources:get"], ["resources:get"])

    def test_check_authentication(self):
        self.clear_lru_cache()

        with self.assertRaises(HTTPException) as he:
            check_authentication(user_name="fails", password="test123")
        self.assertEqual(he.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(he.exception.detail, "Incorrect username or password")

        self.clear_lru_cache()
        with self.assertRaises(HTTPException) as he:
            check_authentication(user_name="test", password="test123")
        self.assertEqual(he.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(he.exception.detail, "Incorrect username or password")

        self.clear_lru_cache()
        self.assertEqual(
            check_authentication(user_name="test", password="test"),
            {
                "hashed_password": "$2b$12$Gkl8KYNGRMhx4kB0bKJnyuRuzOrx3LZlWf1CReIsDk9HyWoUGBihG",  # noqa B509
                "scopes": ["resources:get"],
                "user_name": "test",
            },
        )

    def test_get_user(self):
        self.clear_lru_cache()
        self.assertEqual(
            get_user("test"),
            {
                "hashed_password": "$2b$12$Gkl8KYNGRMhx4kB0bKJnyuRuzOrx3LZlWf1CReIsDk9HyWoUGBihG",  # noqa B509
                "scopes": ["resources:get"],
                "user_name": "test",
            },
        )

        self.clear_lru_cache()
        self.mock_config.side_effect = AttributeError
        with self.assertRaises(TardisError):
            get_user("test")
        self.mock_config.side_effect = None

    @patch("tardis.rest.app.security.gensalt")
    def test_hash_password(self, mocked_gensalt):
        mocked_gensalt.return_value = b"$2b$12$aQ1hv6.1AJSfLL/u4ttm7u"
        self.assertEqual(
            hash_password("test123"),
            b"$2b$12$aQ1hv6.1AJSfLL/u4ttm7uyhV2r1fDdzUw2719FE7Fznq9w6EK1xe",
        )
