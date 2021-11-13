from ...configuration.configuration import Configuration
from ...exceptions.tardisexceptions import TardisError

from bcrypt import checkpw, gensalt, hashpw
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Optional


class TokenData(BaseModel):
    user_name: Optional[str] = None
    scopes: List[str] = []


class UserCredentials(BaseModel):
    user_name: str
    hashed_password: str
    scopes: List[str]

    class Config:
        extra = "forbid"


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login/access-token",
    scopes={
        "user:read": "Read access to database",
        "user:write": "Write access to database.",
    },
)


def create_access_token(
    user_name: str,
    scopes: List[str],
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
) -> str:
    to_encode = {"sub": user_name, "scopes": scopes}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        secret_key or get_secret_key(),
        algorithm=algorithm or get_algorithm(),
    )

    return encoded_jwt


def check_authorization(
    security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme)
) -> TokenData:
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[get_algorithm()])
        user_name: str = payload.get("sub")
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, user_name=user_name)
    except (JWTError, ValidationError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": authenticate_value},
        ) from err

    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            ) from None

    return token_data


def check_authentication(user_name: str, password: str) -> UserCredentials:
    user = get_user(user_name)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if checkpw(password.encode(), user.hashed_password.encode()):
        return user
    else:
        raise HTTPException(status_code=400, detail="Incorrect username or password")


@lru_cache(maxsize=1)
def get_algorithm() -> str:
    try:
        rest_service = Configuration().Services.restapi
    except AttributeError:
        raise TardisError(
            "TARDIS RestService not configured while accessing algorithm!"
        ) from None
    else:
        return rest_service.algorithm


@lru_cache(maxsize=1)
def get_secret_key() -> str:
    try:
        rest_service = Configuration().Services.restapi
    except AttributeError:
        raise TardisError(
            "TARDIS RestService not configured while accessing secret_key!"
        ) from None
    else:
        return rest_service.secret_key


@lru_cache(maxsize=16)
def get_user(user_name: str) -> [None, UserCredentials]:
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
