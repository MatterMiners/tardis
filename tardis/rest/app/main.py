from ...__about__ import __version__
from .routers import login, resources

from fastapi import FastAPI

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
    openapi_tags=[
        {
            "name": "resources",
            "description": "Information about the currently managed resources.",
        },
        {
            "name": "login",
            "description": "Handles login and creation of limited duration tokens to access APIs.",  # noqa B509
        },
    ],
)

app.include_router(resources.router)
app.include_router(login.router)
