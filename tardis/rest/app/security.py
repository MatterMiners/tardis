from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import SecurityScopes
from jose import JWTError, jwt

from tardis.rest.app.database import get_user_db
from tardis.rest.app.models import User
from tardis.rest.app.user_manager import ALGORITHM, CustomUserManager, SECRET_KEY


def check_scope_permissions(requested_scopes: list[str], allowed_scopes: list[str]):
    for scope in requested_scopes:
        if scope not in allowed_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{scope}' not assigned to user",
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
    db_gen = get_user_db()
    try:
        db = await db_gen.__anext__()
        user_manager = CustomUserManager(db)
        user = await user_manager.get_by_id(user_id)
        if user:
            user.scopes = scopes
        return user
    finally:
        # Ensure the async generator is closed immediately so the inner
        # `async with session_factory()` block in get_user_db() runs its
        # __aexit__ and releases the DB session. Without this, the early
        # return above would leave the generator suspended and the session
        # would leak until garbage collection.
        await db_gen.aclose()


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
