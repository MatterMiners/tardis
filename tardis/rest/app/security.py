from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    APIKeyCookie,
    HTTPAuthorizationCredentials,
    HTTPBearer,
    SecurityScopes,
)
from jose import JWTError

from tardis.rest.app.database import get_user_session_factory
from tardis.rest.app.models import User
from tardis.rest.app.user_manager import (
    ACCESS_TOKEN_TYPE,
    CustomUserManager,
    decode_token,
)


def check_scope_permissions(requested_scopes: list[str], allowed_scopes: list[str]):
    for scope in requested_scopes:
        if scope not in allowed_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{scope}' not assigned to user",
            )


# Both schemes are optional, since an access token can be passed either way.
# Declaring them makes them visible in the OpenAPI schema, which enables the
# "Authorize" button of the interactive documentation at /docs.
bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    description="Access token obtained via POST /user/token",
    auto_error=False,
)
cookie_scheme = APIKeyCookie(
    name="tardis_access_token",
    description="Access token cookie set by POST /user/login",
    auto_error=False,
)


async def get_user_from_request(
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    cookie_token: Annotated[str | None, Depends(cookie_scheme)],
) -> User | None:
    # HTTPBearer handles the scheme case-insensitively (RFC 9110, section 11.1)
    token = bearer.credentials if bearer else cookie_token

    if not token:
        return None

    try:
        payload = decode_token(token, ACCESS_TOKEN_TYPE)
        user_id = int(payload["sub"])
        user_name = payload["username"]
    except (JWTError, ValueError, TypeError, KeyError):
        return None
    scopes = payload.get("scopes", [])
    async with get_user_session_factory()() as db:
        user = await CustomUserManager(db).get_by_id(user_id)
        if user and user.user_name != user_name:
            # The token was issued for another user with the same id
            return None
        if user:
            # Detach the user so the token scopes are never written back
            db.expunge(user)
            # Scopes revoked since the token was issued are no longer granted
            user.scopes = [scope for scope in scopes if scope in user.scopes]
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
    security_scopes: SecurityScopes,
    user: Annotated[User | None, Depends(get_user_from_request)],
) -> User:
    """
    Retrieve current authenticated user and enforce scope requirements.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if security_scopes.scopes:
        check_scope_permissions(security_scopes.scopes, user.scopes)

    return user
