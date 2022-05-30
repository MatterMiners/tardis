from .. import security
from fastapi import APIRouter, Depends
from fastapi_jwt_auth import AuthJWT

router = APIRouter(prefix="/user", tags=["user"])

# TODO: Very important: Set the csrf cookie in the frontend.


@router.post("/login", description="Sets httponly access token in session cookie")
async def login(login_user: security.LoginUser, Authorize: AuthJWT = Depends()):
    user = security.check_authentication(
        login_user.user_name, login_user.password)

    scopes = {"scopes": user.scopes}
    access_token = Authorize.create_access_token(
        subject=user.user_name, user_claims=scopes)
    refresh_token = Authorize.create_refresh_token(subject=user.user_name)

    Authorize.set_access_cookies(access_token)
    Authorize.set_refresh_cookies(refresh_token)

    return {"msg": "Successfully logged in!"}


@router.delete('/logout')
async def logout(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()

    Authorize.unset_jwt_cookies()
    return {"msg": "Successfully logged out!"}


@router.post('/refresh')
async def refresh(Authorize: AuthJWT = Depends()):
    Authorize.jwt_refresh_token_required()

    current_user = Authorize.get_jwt_subject()
    new_access_token = Authorize.create_access_token(subject=current_user)

    Authorize.set_access_cookies(new_access_token)
    return {"msg": "Token successfully refreshed"}


@router.get("/me", response_model=security.BaseUser)
async def get_user_me(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()

    user_name = Authorize.get_jwt_subject()
    return security.get_user(user_name)
