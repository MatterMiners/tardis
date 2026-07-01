from typing import Annotated

from .. import crud, database, security
from ....plugins.sqliteregistry import SqliteRegistry
from fastapi import APIRouter, Depends, HTTPException, Path, Security, status
from fastapi.security import SecurityScopes
from ..scopes import Resources

from ..models import User

router = APIRouter(prefix="/resources", tags=["resources"])


async def get_current_user_with_scope(
    user: User = Depends(security.get_user_from_request),
    security_scopes: SecurityScopes = None,
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if security_scopes:
        security.check_scope_permissions(security_scopes.scopes, user.scopes)
    return user


@router.get("/{drone_uuid}/state", description="Get current state of a resource")
async def get_resource_state(
    drone_uuid: str = Path(..., pattern=r"^\S+-[A-Fa-f0-9]{10}$"),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    user: User = Security(get_current_user_with_scope, scopes=[Resources.get]),
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
    user: User = Security(get_current_user_with_scope, scopes=[Resources.get]),
):
    query_result = await crud.get_resources(sql_registry)
    return query_result


@router.patch("/{drone_uuid}/drain", description="Gently shut shown drone")
async def drain_drone(
    drone_uuid: str = Path(..., pattern=r"^\S+-[A-Fa-f0-9]{10}$"),
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    user: User = Security(get_current_user_with_scope, scopes=[Resources.patch]),
):
    await crud.set_state_to_draining(sql_registry, drone_uuid)
    return {"msg": "Drone set to DrainState"}