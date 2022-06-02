from ..scopes import User
from .. import security
from fastapi import APIRouter, Depends, Security
from fastapi_jwt_auth import AuthJWT

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/login", description="Sets httponly access token in session cookie")
async def login(
    login_user: security.LoginUser,
    Authorize: AuthJWT = Depends(),
):
    user = security.check_authentication(login_user.user_name, login_user.password)

    if login_user.scopes == None:
        scopes = {"scopes": user.scopes}
    else:
        # The next two lines are very critical as if wrongly implemented a user can give his token unlimited scopes.
        # This functionality has to be tested thoroughly
        security.check_scope_permissions(login_user.scopes, user.scopes)
        scopes = {"scopes": login_user.scopes}

    access_token = Authorize.create_access_token(
        subject=user.user_name, user_claims=scopes
    )
    refresh_token = Authorize.create_refresh_token(subject=user.user_name)

    Authorize.set_access_cookies(access_token)
    Authorize.set_refresh_cookies(refresh_token)

    return {"msg": "Successfully logged in!"}


@router.delete(
    "/logout",
    description="Logout the current user by deleting all access token cookies",
)
async def logout(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()

    Authorize.unset_jwt_cookies()
    return {"msg": "Successfully logged out!"}


@router.post(
    "/refresh", description="Use refresh token cookie to refresh expiration on cookie"
)
async def refresh(Authorize: AuthJWT = Depends()):
    Authorize.jwt_refresh_token_required()

    current_user = Authorize.get_jwt_subject()
    new_access_token = Authorize.create_access_token(subject=current_user)

    Authorize.set_access_cookies(new_access_token)
    return {"msg": "Token successfully refreshed"}


@router.get(
    "/me",
    response_model=security.BaseUser,
    description="Get the user data how it's stored in the database (no password)",
)
async def get_user_me(
    Authorize: AuthJWT = Security(security.check_authorization, scopes=[User.get]),
):
    Authorize.jwt_required()

    user_name = Authorize.get_jwt_subject()
    return security.get_user(user_name)


@router.get("/token_scopes", description="get scopes of CURRENT token (not of user)")
async def get_token_scopes():
    pass
