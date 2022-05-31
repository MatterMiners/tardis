from ...__about__ import __version__
from .routers import resources, user
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi import Request
from fastapi.responses import JSONResponse

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
            "name": "user",
            "description": "Handles login, refresh tokens, logout and anything related to the user.",  # noqa B509
        },
    ],
)


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(resources.router)
app.include_router(user.router)
