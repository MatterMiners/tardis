from . import crud
from . import database
from . import security
from ..plugins.sqliteregistry import SqliteRegistry
from fastapi import Depends, FastAPI, HTTPException, Path, Security


app = FastAPI()


@app.get("/state/{drone_uuid}")
async def get_state(
    drone_uuid: str = Path(..., regex=r"^\S+-[A-Fa-f0-9]{10}$"),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: str = Security(security.check_authorization, scopes=["user:read"]),
):
    query_result = await crud.get_resource_state(sql_registry, drone_uuid)
    try:
        query_result = query_result[0]
    except IndexError:
        raise HTTPException(status_code=404, detail="Drone not found") from None
    return query_result
