from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel

from tardis.rest.app.database import get_user_db
from tardis.rest.app.models import User
from tardis.rest.app.scopes import User as UserScopes
from tardis.rest.app.user_manager import (
    CustomUserManager,
    decode_token,
)

router = APIRouter(prefix="/user", tags=["user"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginUser(BaseModel):
    user_name: str
    password: str
    scopes: list[str] | None = None


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
            user = await user_manager.get_by_id(user_id)
            return user
    except Exception:
        return None


async def get_current_active_user(
    user: Annotated[User, Depends(get_user_from_request)],
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    login_user: LoginUser,
    authorization: Annotated[str | None, Header()] = None,
):
    async for db in get_user_db():
        user_manager = CustomUserManager(db)
        user = await user_manager.authenticate(
            login_user.user_name, login_user.password
        )
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

        use_bearer = authorization and authorization.startswith("Bearer ")

        if use_bearer:
            access_token = user_manager.create_access_token(user, expires_delta=86400)
            return TokenResponse(access_token=access_token)
        else:
            access_token = user_manager.create_access_token(user, expires_delta=900)
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
            return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="tardis_access_token")
    response.delete_cookie(key="tardis_refresh_token")
    return {"msg": "Successfully logged out!"}


@router.post("/refresh")
async def refresh(
    response: Response,
    request: Request,
):
    refresh_token = request.cookies.get("tardis_refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        payload = decode_token(refresh_token)
        user_id = int(payload.get("sub"))
        async for db in get_user_db():
            user_manager = CustomUserManager(db)
            user = await user_manager.get_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )
            access_token = user_manager.create_access_token(user, expires_delta=900)
            response.set_cookie(
                key="tardis_access_token",
                value=access_token,
                httponly=True,
                samesite="lax",
                secure=False,
            )
            return {"msg": "Token successfully refreshed"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from None


class UserResponse(BaseModel):
    user_name: str
    scopes: list[str]

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if UserScopes.get not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return UserResponse(user_name=current_user.user_name, scopes=current_user.scopes)


@router.get("/token_scopes")
async def get_token_scopes(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user.scopes
