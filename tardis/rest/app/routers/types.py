from typing import Dict, List
from tardis.exceptions.tardisexceptions import TardisError
from .. import crud, database, security
from ....plugins.sqliteregistry import SqliteRegistry
from fastapi import APIRouter, Depends, Security
from fastapi.security import SecurityScopes

from ..models import User
from ..scopes import Resources

router = APIRouter(prefix="/types", tags=["types", "resources"])


def sql_to_list(query_result: List[Dict]) -> List[str]:
    try:
        return [list(pair.values())[0] for pair in query_result]
    except (AttributeError, IndexError, TypeError) as e:
        raise TardisError(
            f"Query result has invalid type/format: {type(query_result)}"
        ) from e


async def get_current_user_with_scope(
    user: User = Depends(security.get_user_from_request),
    security_scopes: SecurityScopes = None,
) -> User:
    if user is None:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if security_scopes:
        security.check_scope_permissions(security_scopes.scopes, user.scopes)
    return user


@router.get("/states", description="Get all available states")
async def get_resource_state(
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    user: User = Security(get_current_user_with_scope, scopes=[Resources.get]),
):
    query_result = await crud.get_available_states(sql_registry)
    return sql_to_list(query_result)


@router.get("/sites", description="Get all available sites")
async def get_resource_sites(
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    user: User = Security(get_current_user_with_scope, scopes=[Resources.get]),
):
    query_result = await crud.get_available_sites(sql_registry)
    return sql_to_list(query_result)


@router.get("/machine_types", description="Get all available machine types")
async def get_resource_types(
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    user: User = Security(get_current_user_with_scope, scopes=[Resources.get]),
):
    query_result = await crud.get_available_machine_types(sql_registry)
    return sql_to_list(query_result)
