from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import SecurityScopes
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
)
from fastapi_users.authentication.strategy.jwt import JWTStrategy

from tardis.rest.app.database import get_user_db
from tardis.rest.app.models import User
from tardis.rest.app.user_manager import ALGORITHM, CustomUserManager, SECRET_KEY
from jose import JWTError, jwt
from fastapi_users.jwt import generate_jwt


class ScopedJWTStrategy(JWTStrategy):
    async def write_token(self, user: User) -> str:
        data = {
            "sub": str(user.id),
            "aud": self.token_audience,
            "scopes": user.scopes,
        }
        return generate_jwt(
            data, self.encode_key, self.lifetime_seconds, algorithm=self.algorithm
        )


cookie_backend = AuthenticationBackend(
    name="cookie",
    transport=CookieTransport(),
    get_strategy=lambda: ScopedJWTStrategy(
        secret=SECRET_KEY,
        algorithm=ALGORITHM,
        lifetime_seconds=900,
    ),
)

bearer_backend = AuthenticationBackend(
    name="bearer",
    transport=BearerTransport(tokenUrl="/user/login"),
    get_strategy=lambda: ScopedJWTStrategy(
        secret=SECRET_KEY,
        algorithm=ALGORITHM,
        lifetime_seconds=86400,
    ),
)


def check_scope_permissions(requested_scopes: list, allowed_scopes: list):
    for requested_scope in requested_scopes:
        if requested_scope not in allowed_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "msg": "Not enough permissions",
                    "failedAt": requested_scope,
                    "allowedScopes": allowed_scopes,
                },
            )


async def get_user_from_request(request: Request) -> User | None:
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif "tardis_access_token" in request.cookies:
        token = request.cookies.get("tardis_access_token")

    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, ValueError, TypeError, KeyError):
        return None
    scopes = payload.get("scopes", [])
    async for db in get_user_db():
        user_manager = CustomUserManager(db)
        user = await user_manager.get_by_id(user_id)
        if user:
            user.scopes = scopes
        return user


async def get_current_active_user(
    user: Annotated[User | None, Depends(get_user_from_request)],
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


async def get_current_user_with_scopes(
    user: Annotated[User | None, Depends(get_user_from_request)],
    security_scopes: SecurityScopes | None = None,
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if security_scopes:
        check_scope_permissions(security_scopes.scopes, user.scopes)
    return user
