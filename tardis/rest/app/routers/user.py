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
