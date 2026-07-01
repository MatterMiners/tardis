from sqlalchemy import String, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import List


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_name: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    scopes: Mapped[List[str]] = mapped_column(JSON, default=list)
