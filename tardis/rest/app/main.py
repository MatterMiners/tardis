from contextlib import asynccontextmanager

from ...__about__ import __version__
from fastapi import FastAPI

from .database import init_user_db, dispose_user_db_engine
from .routers import resources, types, user


@asynccontextmanager
async def init_user_db_lifespan(app: FastAPI):
    await init_user_db()
    yield
    await dispose_user_db_engine()


app = FastAPI(
    title="TARDIS REST API",
    version=__version__,
    description="",
    contact={
        "name": "Matterminers",
        "url": "https://matterminers.github.io/",
        "email": "matterminers@lists.kit.edu",
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/MatterMiners/tardis/blob/master/LICENSE.txt",
    },
    lifespan=init_user_db_lifespan,
    openapi_tags=[
        {
            "name": "resources",
            "description": "Information about the currently managed resources.",
        },
        {
            "name": "user",
            "description": "Handles login, refresh tokens, logout and anything related to the user.",  # noqa: B950
        },
    ],
)

app.include_router(resources.router)
app.include_router(user.router)
app.include_router(types.router)
