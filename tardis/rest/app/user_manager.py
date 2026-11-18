import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from functools import cache
from typing import Optional

from bcrypt import checkpw, gensalt, hashpw
from jose import jwt
from jose.exceptions import JWTClaimsError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tardis.rest.app.models import User

SECRET_KEY = secrets.token_hex(128)
ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
# bcrypt only supports passwords of up to 72 bytes
MAX_PASSWORD_BYTES = 72


def password_too_long(password: str) -> bool:
    return len(password.encode()) > MAX_PASSWORD_BYTES


@cache
def _dummy_password_hash() -> str:
    """Hash to check passwords of unknown users against, see authenticate()"""
    return hashpw(secrets.token_bytes(16), gensalt()).decode()


class CustomUserManager:
    def __init__(self, user_db: AsyncSession):
        self.user_db = user_db

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        # No stored password can be that long, and bcrypt would raise
        if password_too_long(plain_password):
            return False
        return checkpw(plain_password.encode(), hashed_password.encode())

    @staticmethod
    def get_password_hash(password: str) -> str:
        if password_too_long(password):
            raise ValueError(
                f"Password must be at most {MAX_PASSWORD_BYTES} bytes (UTF-8)"
            )
        return hashpw(password.encode(), gensalt()).decode()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.user_db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.user_db.execute(
            select(User).where(User.user_name == username)
        )
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        user = await self.get_by_username(username)
        # bcrypt is slow by design, run it in a thread to keep the event loop
        # responsive, which TARDIS shares with all other asyncio services
        valid = await asyncio.to_thread(
            self._check_password, password, user.hashed_password if user else None
        )
        return user if user and valid else None

    def _check_password(self, password: str, hashed_password: Optional[str]) -> bool:
        if hashed_password is None:
            # Check against a dummy hash, so that unknown users take as long as
            # known ones and the response time does not reveal valid user names
            self.verify_password(password, _dummy_password_hash())
            return False
        return self.verify_password(password, hashed_password)

    async def create(
        self, user_name: str, password: str, scopes: Optional[list[str]] = None
    ) -> User:
        user = User(
            user_name=user_name,
            hashed_password=self.get_password_hash(password),
            scopes=scopes or [],
        )
        self.user_db.add(user)
        await self.user_db.commit()
        await self.user_db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.user_db.delete(user)
        await self.user_db.commit()

    async def list_all(self) -> list[User]:
        result = await self.user_db.execute(select(User))
        return list(result.scalars().all())

    def create_access_token(
        self, user: User, expires_delta: int = 900, scopes: Optional[list[str]] = None
    ) -> str:
        data = {
            "sub": str(user.id),
            "username": user.user_name,
            "scopes": scopes if scopes is not None else user.scopes,
            "type": ACCESS_TOKEN_TYPE,
        }
        return self._create_token(data, expires_delta)

    def create_refresh_token(
        self, user: User, expires_delta: int = 3600, scopes: Optional[list[str]] = None
    ) -> str:
        data = {
            "sub": str(user.id),
            "username": user.user_name,
            "scopes": scopes if scopes is not None else user.scopes,
            "type": REFRESH_TOKEN_TYPE,
        }
        return self._create_token(data, expires_delta)

    def _create_token(self, data: dict, expires_delta: int) -> str:
        expire = datetime.now(timezone.utc) + timedelta(seconds=expires_delta)
        data["exp"] = expire
        return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    """
    Decode and verify a token and check that it is of the expected type.

    Raises a JWTError if the token is invalid, expired or of another type, so
    that a refresh token cannot be used as an access token and vice versa.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise JWTClaimsError(f"Token is not of type '{expected_type}'")
    return payload
