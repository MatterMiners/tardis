import secrets
from ...configuration.configuration import Configuration
from ...exceptions.tardisexceptions import TardisError

from bcrypt import checkpw, gensalt, hashpw
from fastapi import HTTPException, status, Depends

from fastapi.security import SecurityScopes

from pydantic import BaseModel
from fastapi_jwt_auth import AuthJWT

from functools import lru_cache
from typing import List, Optional


class Settings(BaseModel):
    authjwt_secret_key: str = secrets.token_hex(128)
    authjwt_token_location: set = {"cookies"}
    authjwt_cookie_samesite: str = "strict"
    # TODO: change this to true in production so only https traffic is allowed
    # Service meant to be used with https proxy
    authjwt_cookie_secure: bool = False
    # As 'same_site' is strict this is probably enough.
    authjwt_cookie_csrf_protect: bool = False


@AuthJWT.load_config
def get_config():
    # TODO: Solve - AttributeError: Configuration().Services
    return Settings()


class BaseUser(BaseModel):
    user_name: str
    scopes: Optional[List[str]] = None


# TODO: Document the scopes manually
# "resources:get": "Allows to read resource database",
# "resources:put": "Allows to update resource database.",


class LoginUser(BaseUser):
    password: str


class DatabaseUser(BaseUser):
    hashed_password: str


def check_scope_permissions(requested_scopes: List[str], allowed_scopes: List[str]):
    # All requested scopes must be contained in allowed_scopes
    for scope in requested_scopes:
        if scope not in allowed_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "msg": "Not enough permissions",
                    "failedAt": scope,
                    "allowedScopes": allowed_scopes,
                },
            ) from None


def check_authorization(
    security_scopes: SecurityScopes, Authorize: AuthJWT = Depends()
) -> AuthJWT:
    # No authorization without authentication
    Authorize.jwt_required()

    token_scopes = get_token_scopes(Authorize)
    check_scope_permissions(security_scopes.scopes, token_scopes)

    return Authorize


def check_authentication(user_name: str, password: str) -> DatabaseUser:
    user = get_user(user_name)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if checkpw(password.encode(), user.hashed_password.encode()):
        return user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )


def get_token_scopes(Authorize: AuthJWT) -> List[str]:
    try:
        token_scopes: List[str] = Authorize.get_raw_jwt()["scopes"]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token/no scopes in token",
        ) from None
    return token_scopes


@lru_cache(maxsize=16)
def get_user(user_name: str) -> Optional[DatabaseUser]:
    try:
        rest_service = Configuration().Services.restapi
    except AttributeError:
        raise TardisError(
            "TARDIS RestService not configured while accessing user credentials"
        ) from None
    else:
        return rest_service.get_user(user_name)


def hash_password(password: str) -> bytes:
    salt = gensalt()
    return hashpw(password.encode(), salt)
