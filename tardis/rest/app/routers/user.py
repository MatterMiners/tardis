from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    Security,
    status,
)
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from tardis.rest.app.database import get_user_db
from tardis.rest.app.models import User
from tardis.rest.app.schemas import LoginUser, TokenResponse, UserResponse
from tardis.rest.app.scopes import UserScopes
from tardis.rest.app.security import (
    check_scope_permissions,
    get_current_active_user,
    get_current_user_with_scopes,
)
from tardis.rest.app.user_manager import (
    REFRESH_TOKEN_TYPE,
    CustomUserManager,
    decode_token,
)

router = APIRouter(prefix="/user", tags=["user"])

ACCESS_COOKIE = "tardis_access_token"
REFRESH_COOKIE = "tardis_refresh_token"

_SECURE_COOKIE = None


def _get_secure_cookie() -> bool:
    global _SECURE_COOKIE
    if _SECURE_COOKIE is None:
        from ..database import get_development_mode

        _SECURE_COOKIE = not get_development_mode()
    return _SECURE_COOKIE


def _set_auth_cookie(response: Response, key: str, value: str):
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        samesite="lax",
        secure=_get_secure_cookie(),
    )


def _delete_auth_cookie(response: Response, key: str):
    # Use the same attributes as in _set_auth_cookie
    response.delete_cookie(
        key=key,
        httponly=True,
        samesite="lax",
        secure=_get_secure_cookie(),
    )


def _requested_scopes(login_user: LoginUser, user: User) -> list[str]:
    """
    Scopes for a new token: all scopes of the user if none are requested,
    otherwise the requested ones, which must all be assigned to the user.
    An explicitly empty list results in a token without scopes.
    """
    requested = user.scopes if login_user.scopes is None else login_user.scopes
    check_scope_permissions(requested, user.scopes)
    return requested


@router.post("/login")
async def login(
    response: Response,
    login_user: LoginUser,
    db: AsyncSession = Depends(get_user_db),
):
    user_manager = CustomUserManager(db)
    user = await user_manager.authenticate(login_user.user_name, login_user.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    requested_scopes = _requested_scopes(login_user, user)

    access_token = user_manager.create_access_token(
        user, expires_delta=900, scopes=requested_scopes
    )
    refresh_token = user_manager.create_refresh_token(
        user, expires_delta=3600, scopes=requested_scopes
    )
    _set_auth_cookie(response, ACCESS_COOKIE, access_token)
    _set_auth_cookie(response, REFRESH_COOKIE, refresh_token)
    return {"msg": "Login successful"}


@router.post("/token", response_model=TokenResponse)
async def token(
    login_user: LoginUser,
    db: AsyncSession = Depends(get_user_db),
):
    user_manager = CustomUserManager(db)
    user = await user_manager.authenticate(login_user.user_name, login_user.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    requested_scopes = _requested_scopes(login_user, user)

    access_token = user_manager.create_access_token(
        user, expires_delta=86400, scopes=requested_scopes
    )
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    _delete_auth_cookie(response, ACCESS_COOKIE)
    _delete_auth_cookie(response, REFRESH_COOKIE)
    return {"msg": "Successfully logged out!"}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_user_db),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        user_id = int(payload["sub"])
        user_name = payload["username"]
        token_scopes = payload.get("scopes", [])
    except (JWTError, ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from None
    user_manager = CustomUserManager(db)
    user = await user_manager.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if user.user_name != user_name:
        # The token was issued for another user with the same id
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    check_scope_permissions(token_scopes, user.scopes)
    access_token = user_manager.create_access_token(
        user, expires_delta=900, scopes=token_scopes
    )
    _set_auth_cookie(response, ACCESS_COOKIE, access_token)
    return {"msg": "Token successfully refreshed"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Security(get_current_user_with_scopes, scopes=[UserScopes.get])
):
    return UserResponse(user_name=current_user.user_name, scopes=current_user.scopes)


@router.get("/scopes")
async def get_scopes(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user.scopes
