from ..configuration.configuration import Configuration

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Optional


class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "user:read": "Read access to database",
        "user:write": "Write access to database.",
    },
)


def create_access_token(user_name, scopes, expires_delta: Optional[timedelta] = None):
    to_encode = {"sub": user_name, "scopes": scopes}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=get_algorithm())

    return encoded_jwt


def check_authorization(
    security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme)
):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[get_algorithm()])
        username: str = payload.get("sub")
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=username)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": authenticate_value},
        )

    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )

    return token_data


@lru_cache(maxsize=1)
def get_algorithm():
    try:
        rest_service = Configuration().Services.restapi
    except AttributeError:
        pass
    else:
        return rest_service.algorithm


@lru_cache(maxsize=1)
def get_secret_key():
    try:
        rest_service = Configuration().Services.restapi
    except AttributeError:
        pass
    else:
        return rest_service.secret_key
