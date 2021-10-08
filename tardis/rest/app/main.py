from .routers import resources
from fastapi import FastAPI

app = FastAPI()

app.include_router(resources.router)
