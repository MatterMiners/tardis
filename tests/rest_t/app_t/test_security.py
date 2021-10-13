from tardis.exceptions.tardisexceptions import TardisError
from tardis.rest.app.security import (
    create_access_token,
    check_authorization,
    check_authentication,
    get_algorithm,
    get_secret_key,
    get_user,
    hash_password,
    TokenData,
)
from tardis.utilities.attributedict import AttributeDict

from fastapi import HTTPException, status
from fastapi.security import SecurityScopes
from jose import JWTError

from datetime import datetime, timedelta
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
        self.secret_key = (
            "689e7af69a70ad0d97f771371738be00452e81e128a876491c1d373dfbcca949"
        )
        self.algorithm = "HS256"

        self.infinite_read_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbInVzZXI6cmVhZCJdfQ.qO2ikdmETwmK-mzsKUEIL1QA47LF-OgCXNssGIarPLM"  # noqa B950
        self.limited_read_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbInVzZXI6cmVhZCJdLCJleHAiOjkwMH0.rP-2IlCoEDTMeo5D70FuQ7jfLoQpRYSSAlU-zIIo2iw"  # noqa B950
        self.infinite_rw_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbInVzZXI6cmVhZCIsInVzZXI6d3JpdGUiXX0.vFUbHA5BFOCgWmjBWUTS5PRLDmKuvGmWk81_FtKFCA0"  # noqa B950

        def mocked_get_user(user_name):
            if user_name == "test":
                return AttributeDict(
                    user_name="test",
                    hashed_password="$2b$12$Gkl8KYNGRMhx4kB0bKJnyuRuzOrx3LZlWf1CReIsDk9HyWoUGBihG",  # noqa B509
                    scopes=["user:read"],
                )
            return None

        config = self.mock_config.return_value
        config.Services.restapi.secret_key = self.secret_key
        config.Services.restapi.algorithm = self.algorithm
        config.Services.restapi.get_user.side_effect = mocked_get_user

    @staticmethod
    def clear_lru_cache():
        get_algorithm.cache_clear()
        get_secret_key.cache_clear()
        get_user.cache_clear()

    @patch("tardis.rest.app.security.datetime")
    def test_create_access_token(self, mocked_datetime):
        self.clear_lru_cache()

        token = create_access_token(user_name="test", scopes=["user:read"])
        self.assertEqual(token, self.infinite_read_token)

        self.clear_lru_cache()

        token = create_access_token(
            user_name="test",
            scopes=["user:read"],
            secret_key="c2ac5e498f6287c58fa941d0d2cfaf2dc271762a7ba03dcfc3ceb91bb1895d05",  # noqa B950
            algorithm=self.algorithm,
        )

        self.assertEqual(
            token,
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbInVzZXI6cmVhZCJdfQ.qlqyNAoZD0DGO5ib5jyfcNULDsrLo_YkPjiIqJWNTs0",  # noqa B950
        )

        self.clear_lru_cache()
        mocked_datetime.utcnow.return_value = datetime.utcfromtimestamp(0)
        token = create_access_token(
            user_name="test",
            scopes=["user:read"],
            expires_delta=timedelta(minutes=15),
        )

        self.assertEqual(token, self.limited_read_token)

        self.clear_lru_cache()
        token = create_access_token(
            user_name="test", scopes=["user:read", "user:write"]
        )

        self.assertEqual(token, self.infinite_rw_token)

    def test_check_authorization(self):
        self.clear_lru_cache()
        security_scopes = SecurityScopes(["user:read"])
        token_data = check_authorization(security_scopes, self.infinite_read_token)

        self.assertEqual(
            token_data, TokenData(scopes=security_scopes.scopes, user_name="test")
        )

        security_scopes = SecurityScopes(["user:write"])
        with self.assertRaises(HTTPException) as he:
            check_authorization(security_scopes, self.infinite_read_token)
        self.assertEqual(he.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(he.exception.detail, "Not enough permissions")

        token_data = check_authorization(security_scopes, self.infinite_rw_token)
        self.assertEqual(
            token_data, TokenData(scopes=["user:read", "user:write"], user_name="test")
        )

        security_scopes = SecurityScopes()
        check_authorization(security_scopes, self.infinite_read_token)

        with self.assertRaises(HTTPException) as he:
            check_authorization(security_scopes, "1234567890abdcef")
        self.assertEqual(he.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(he.exception.detail, "Could not validate credentials")

    @patch("tardis.rest.app.security.jwt")
    def test_check_authorization_jwt_error(self, mocked_jwt):
        mocked_jwt.decode.side_effect = JWTError

        with self.assertRaises(HTTPException) as he:
            check_authorization(SecurityScopes(), self.infinite_read_token)
        self.assertEqual(he.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(he.exception.detail, "Could not validate credentials")

        mocked_jwt.decode.side_effect = None

    def test_check_authentication(self):
        self.clear_lru_cache()

        with self.assertRaises(HTTPException) as he:
            check_authentication(user_name="fails", password="test123")
        self.assertEqual(he.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(he.exception.detail, "Incorrect username or password")

        self.clear_lru_cache()
        with self.assertRaises(HTTPException) as he:
            check_authentication(user_name="test", password="test123")
        self.assertEqual(he.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(he.exception.detail, "Incorrect username or password")

        self.clear_lru_cache()
        self.assertEqual(
            check_authentication(user_name="test", password="test"),
            {
                "hashed_password": "$2b$12$Gkl8KYNGRMhx4kB0bKJnyuRuzOrx3LZlWf1CReIsDk9HyWoUGBihG",  # noqa B509
                "scopes": ["user:read"],
                "user_name": "test",
            },
        )

    def test_get_algorithm(self):
        self.clear_lru_cache()
        self.assertEqual(get_algorithm(), self.algorithm)

        self.clear_lru_cache()
        self.mock_config.side_effect = AttributeError
        with self.assertRaises(TardisError):
            get_algorithm()
        self.mock_config.side_effect = None

    def test_get_secret_key(self):
        self.clear_lru_cache()
        self.assertEqual(get_secret_key(), self.secret_key)

        self.clear_lru_cache()
        self.mock_config.side_effect = AttributeError
        with self.assertRaises(TardisError):
            get_secret_key()
        self.mock_config.side_effect = None

    def test_get_user(self):
        self.clear_lru_cache()
        self.assertEqual(
            get_user("test"),
            {
                "hashed_password": "$2b$12$Gkl8KYNGRMhx4kB0bKJnyuRuzOrx3LZlWf1CReIsDk9HyWoUGBihG",  # noqa B509
                "scopes": ["user:read"],
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
