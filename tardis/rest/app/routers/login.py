from .. import security
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from datetime import timedelta

router = APIRouter(prefix="/login", tags=["login"])


@router.post("/access-token", description="Get a limited duration access token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = security.check_authentication(form_data.username, form_data.password)
    return {
        "access_token": security.create_access_token(
            user.user_name, user.scopes, expires_delta=timedelta(days=1)
        ),
        "token_type": "bearer",
    }
