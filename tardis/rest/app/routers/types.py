from typing import Dict, List
from tardis.exceptions.tardisexceptions import TardisError
from .. import security
from .. import crud, database
from ....plugins.sqliteregistry import SqliteRegistry
from fastapi import APIRouter, Depends, Security
from ..scopes import Resources
from fastapi_jwt_auth import AuthJWT

router = APIRouter(prefix="/types", tags=["types", "resources"])


def sql_to_list(query_result: List[Dict]) -> List[str]:
    try:
        return [list(pair.values())[0] for pair in query_result]
    except (AttributeError, IndexError, TypeError) as e:
        raise TardisError(
            f"Query result has invalid type/format: {type(query_result)}. Must be List[Dict]"  # noqa B950
        ) from e


@router.get("/states", description="Get all available states")
async def get_resource_state(
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.get]),
):
    query_result = await crud.get_available_states(sql_registry)
    return sql_to_list(query_result)


@router.get("/sites", description="Get all available sites")
async def get_resource_sites(
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.get]),
):
    query_result = await crud.get_available_sites(sql_registry)
    return sql_to_list(query_result)


@router.get("/machine_types", description="Get all available machine types")
async def get_resource_types(
    sql_registry: SqliteRegistry = Depends(database.get_sql_registry()),
    _: AuthJWT = Security(security.check_authorization, scopes=[Resources.get]),
):
    query_result = await crud.get_available_machine_types(sql_registry)
    return sql_to_list(query_result)
