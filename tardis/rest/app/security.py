import secrets
from ...configuration.configuration import Configuration
from ...exceptions.tardisexceptions import TardisError

from bcrypt import checkpw, gensalt, hashpw
from fastapi import HTTPException, status, Depends

from fastapi.security import SecurityScopes

from pydantic import BaseModel
from fastapi_jwt_auth import AuthJWT

# from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional, List


class Settings(BaseModel):
    authjwt_secret_key: str = secrets.token_hex(128)
    authjwt_token_location: set = {"cookies"}
    authjwt_cookie_samesite: str = "strict"
    # TODO: change this to true in production so only https traffic is allowed
    authjwt_cookie_secure: bool = False
    # TODO: Set this too to True. But as soon as possible.
    authjwt_cookie_csrf_protect: bool = False


@AuthJWT.load_config
def get_config():
    return Settings()


class BaseUser(BaseModel):
    user_name: str
    scopes: List[str] = []


# TODO: Document the scopes manually
# "resources:get": "Allows to read resource database",
# "resources:put": "Allows to update resource database.",


class LoginUser(BaseUser):
    password: str


class DatabaseUser(BaseUser):
    hashed_password: str


def check_scope_permissions(requested_scopes: List[str], allowed_scopes: List[str]):
    for scope in requested_scopes:
        if scope not in allowed_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            ) from None

#     try:
#         payload = jwt.decode(token, get_secret_key(),
#                              algorithms=[get_algorithm()])
#         user_name: str = payload.get("sub")
#         token_scopes = payload.get("scopes", [])
#         token_data = TokenData(scopes=token_scopes, user_name=user_name)
#     except (JWTError, ValidationError) as err:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials",
#             headers={"WWW-Authenticate": authenticate_value},
#         ) from err

    check_scope_permissions(security_scopes.scopes, token_scopes)

#     return token_data


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


@lru_cache(maxsize=1)
def get_algorithm() -> str:
    # This can probably be deprecated as fastapi_jwt_tokens
    # sets it's algorithm by itself
    try:
        rest_service = Configuration().Services.restapi
    except AttributeError:
        raise TardisError(
            "TARDIS RestService not configured while accessing algorithm!"
        ) from None
    else:
        return rest_service.algorithm


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
