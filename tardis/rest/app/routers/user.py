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
from jose.exceptions import ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

from tardis.rest.app.database import get_user_db
from tardis.rest.app.models import User
from tardis.rest.app.schemas import LoginUser, TokenResponse, UserResponse
from tardis.rest.app.scopes import UserScopes
from tardis.rest.app.security import (
    get_current_active_user,
    get_current_user_with_scopes,
)
from tardis.rest.app.user_manager import CustomUserManager, decode_token

router = APIRouter(prefix="/user", tags=["user"])


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

    requested_scopes = login_user.scopes or user.scopes
    for scope in requested_scopes:
        if scope not in user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{scope}' not assigned to user",
            )

    access_token = user_manager.create_access_token(
        user, expires_delta=900, scopes=requested_scopes
    )
    refresh_token = user_manager.create_refresh_token(user, expires_delta=3600)
    response.set_cookie(
        key="tardis_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    response.set_cookie(
        key="tardis_refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
    )
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

    requested_scopes = login_user.scopes or user.scopes
    for scope in requested_scopes:
        if scope not in user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{scope}' not assigned to user",
            )

    access_token = user_manager.create_access_token(
        user, expires_delta=86400, scopes=requested_scopes
    )
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    response.delete_cookie(key="tardis_access_token")
    response.delete_cookie(key="tardis_refresh_token")
    return {"msg": "Successfully logged out!"}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_user_db),
):
    refresh_token = request.cookies.get("tardis_refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        payload = decode_token(refresh_token)
        user_id = int(payload["sub"])
        token_scopes = payload.get("scopes", [])
    except (ValueError, TypeError, KeyError, ExpiredSignatureError):
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
    access_token = user_manager.create_access_token(
        user, expires_delta=900, scopes=token_scopes
    )
    response.set_cookie(
        key="tardis_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
    )
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
