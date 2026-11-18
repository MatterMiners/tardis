from pydantic import BaseModel


class UserResponse(BaseModel):
    user_name: str
    scopes: list[str]


class LoginUser(BaseModel):
    user_name: str
    password: str
    scopes: list[str] | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
