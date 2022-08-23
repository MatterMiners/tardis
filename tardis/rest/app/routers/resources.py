from .. import security, crud, database
from ....plugins.sqliteregistry import SqliteRegistry
from fastapi import APIRouter, Depends, HTTPException, Path, Security, status
from ..scopes import Resources
from fastapi_jwt_auth import AuthJWT

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/{drone_uuid}/state", description="Get current state of a resource")
async def get_resource_state(
    drone_uuid: str = Path(..., regex=r"^\S+-[A-Fa-f0-9]{10}$"),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.get]),
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
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.get]),
):
    query_result = await crud.get_resources(sql_registry)
    return query_result


@router.patch("/{drone_uuid}/drain", description="Gently shut shown drone")
async def drain_drone(
    drone_uuid: str = Path(..., regex=r"^\S+-[A-Fa-f0-9]{10}$"),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.patch]),
):
    await crud.set_state_to_draining(sql_registry, drone_uuid)
    return {"msg": "Drone set to DrainState"}
