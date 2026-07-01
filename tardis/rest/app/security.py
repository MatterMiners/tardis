from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import SecurityScopes
from fastapi import Request
from fastapi import Header

from tardis.rest.app.models import User
from tardis.rest.app.database import get_user_db
from tardis.rest.app.user_manager import CustomUserManager, decode_token


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


async def get_user_from_request(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    token = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif "tardis_access_token" in request.cookies:
        token = request.cookies.get("tardis_access_token")

    if not token:
        return None

    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
        async for db in get_user_db():
            user_manager = CustomUserManager(db)
            return await user_manager.get_by_id(user_id)
    except Exception:
        return None


async def get_current_active_user(
    user: User = Depends(get_user_from_request),
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


async def get_current_user_with_scopes(
    user: User = Depends(get_user_from_request),
    security_scopes: SecurityScopes = None,
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if security_scopes:
        check_scope_permissions(security_scopes.scopes, user.scopes)
    return user
