from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ...configuration.configuration import Configuration
from ...plugins.sqliteregistry import SqliteRegistry
from tardis.rest.app.models import Base

_user_engine = None
_user_session_factory = None


def get_user_db_engine():
    global _user_engine
    if _user_engine is None:
        user_db_url = Configuration().Services.restapi.user_db_url
        _user_engine = create_async_engine(user_db_url, echo=False)
    return _user_engine


def get_user_session_factory():
    global _user_session_factory
    if _user_session_factory is None:
        _user_session_factory = async_sessionmaker(
            bind=get_user_db_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _user_session_factory


async def init_user_db():
    engine = get_user_db_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_user_db_engine():
    global _user_engine, _user_session_factory
    if _user_engine is not None:
        await _user_engine.dispose()
        _user_engine = None
        _user_session_factory = None


async def get_user_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_user_session_factory()
    async with session_factory() as session:
        yield session


def get_sql_registry():
    sql_registry = SqliteRegistry()
    return lambda: sql_registry
