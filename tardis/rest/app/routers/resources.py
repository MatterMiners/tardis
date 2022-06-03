from .. import security
from .. import crud, database
from ....plugins.sqliteregistry import SqliteRegistry
from fastapi import APIRouter, Depends, HTTPException, Path, Security, status
from ..scopes import Resources

router = APIRouter(prefix="/resources", tags=["resources"])

# TODO: Implement dependency for single drone operations


@router.get("/{drone_uuid}/state", description="Get current state of a resource")
async def get_resource_state(
    drone_uuid: str = Path(..., regex=r"^\S+-[A-Fa-f0-9]{10}$"),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _=Security(security.check_authorization, scopes=[Resources.get]),
):
    query_result = await crud.get_resource_state(sql_registry, drone_uuid)
    try:
        query_result = query_result[0]
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found"
        ) from None
    return query_result


@router.get("/", description="Get list of managed resources")
async def get_resources(
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _=Security(security.check_authorization, scopes=[Resources.get]),
):
    query_result = await crud.get_resources(sql_registry)
    return query_result


@router.delete('/{drone_uuid}/shutdown', description="Gently shut shown drone")
async def shutdown_drone(
    _=Security(security.check_authorization, scopes=[Resources.delete]),
):
    pass
