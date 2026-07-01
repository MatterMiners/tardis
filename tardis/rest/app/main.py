from contextlib import asynccontextmanager

from ...__about__ import __version__
from fastapi import FastAPI

from .database import init_user_db
from .routers import resources, types, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_user_db()
    yield


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
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "resources",
            "description": "Information about the currently managed resources.",
        },
        {
            "name": "user",
            "description": "Handles login, refresh tokens, logout and anything related to the user.",
        },
    ],
)

app.include_router(resources.router)
app.include_router(user.router)
app.include_router(types.router)