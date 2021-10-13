from .. import security, crud, database
from ....plugins.sqliteregistry import SqliteRegistry
from fastapi import APIRouter, Depends, HTTPException, Path, Security


router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/state/{drone_uuid}", description="Get current state of a resource")
async def get_resource_state(
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


@router.get("/", description="Get list of managed resources")
async def get_resources(
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: str = Security(security.check_authorization, scopes=["user:read"]),
):
    query_result = await crud.get_resources(sql_registry)
    return query_result
