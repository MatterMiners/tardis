import secrets
from typing import Optional

from bcrypt import checkpw, gensalt, hashpw
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tardis.rest.app.models import User


SECRET_KEY = secrets.token_hex(128)
ALGORITHM = "HS256"


class CustomUserManager:
    def __init__(self, user_db: AsyncSession):
        self.user_db = user_db

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return checkpw(plain_password.encode(), hashed_password.encode())

    @staticmethod
    def get_password_hash(password: str) -> str:
        return hashpw(password.encode(), gensalt()).decode()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.user_db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.user_db.execute(
            select(User).where(User.user_name == username)
        )
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        user = await self.get_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def create(
        self, user_name: str, password: str, scopes: Optional[list] = None
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

    def create_access_token(self, user: User, expires_delta: int = 900) -> str:
        data = {
            "sub": str(user.id),
            "username": user.user_name,
            "scopes": user.scopes,
        }
        return self._create_token(data, expires_delta)

    def create_refresh_token(self, user: User, expires_delta: int = 3600) -> str:
        data = {
            "sub": str(user.id),
            "username": user.user_name,
            "scopes": user.scopes,
        }
        return self._create_token(data, expires_delta)

    def _create_token(self, data: dict, expires_delta: int) -> str:
        from jose import jwt
        from datetime import datetime, timedelta, timezone

        expire = datetime.now(timezone.utc) + timedelta(seconds=expires_delta)
        data["exp"] = expire
        return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def get_user_manager(user_db: AsyncSession) -> CustomUserManager:
    return CustomUserManager(user_db)


def decode_token(token: str) -> dict:
    from jose import jwt

    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
