from datetime import datetime


async def get_resource_state(sql_registry, drone_uuid: str):
    sql_query = """
    SELECT R.drone_uuid, RS.state
    FROM Resources R
    JOIN ResourceStates RS ON R.state_id = RS.state_id
    WHERE R.drone_uuid = :drone_uuid"""
    return await sql_registry.async_execute(sql_query, dict(drone_uuid=drone_uuid))


async def get_resources(sql_registry):
    sql_query = """
    SELECT R.remote_resource_uuid , RS.state, R.drone_uuid, S.site_name,
    MT.machine_type, R.created, R.updated
    FROM Resources R
    JOIN ResourceStates RS ON R.state_id = RS.state_id
    JOIN Sites S ON R.site_id = S.site_id
    JOIN MachineTypes MT ON R.machine_type_id = MT.machine_type_id"""
    return await sql_registry.async_execute(sql_query, {})


async def get_available_states(sql_registry):
    sql_query = "SELECT state FROM ResourceStates"
    return await sql_registry.async_execute(sql_query, {})


async def get_available_sites(sql_registry):
    sql_query = "SELECT site_name FROM Sites"
    return await sql_registry.async_execute(sql_query, {})


async def get_available_machine_types(sql_registry):
    sql_query = "SELECT machine_type FROM MachineTypes"
    return await sql_registry.async_execute(sql_query, {})


async def get_drone_uuid(sql_registry, remote_resource_uuid: str):
    sql_query = """
    SELECT R.drone_uuid
    FROM Resources R
    WHERE R.remote_resource_uuid = :remote_resource_uuid"""
    return await sql_registry.async_execute(
        sql_query, dict(remote_resource_uuid=remote_resource_uuid)
    )


async def get_shutdown_time(sql_registry, remote_resource_uuid: str):
    sql_query = """
    SELECT R.shutdown_time
    FROM Resources R
    WHERE R.remote_resource_uuid = :remote_resource_uuid"""
    return await sql_registry.async_execute(
        sql_query, dict(remote_resource_uuid=remote_resource_uuid)
    )


async def set_state_to_draining(sql_registry, drone_uuid: str):
    sql_query = """
    UPDATE Resources
    SET state_id = (SELECT state_id FROM ResourceStates WHERE state = 'DrainState')
    WHERE drone_uuid = :drone_uuid"""
    return await sql_registry.async_execute(sql_query, dict(drone_uuid=drone_uuid))


async def assign_shutdown_time(sql_registry, shutdown_time: datetime):
    """
    Assign shutdown_time to the oldest drone still waiting for one, i.e. a
    drone in BootingState without host and without shutdown_time.
    Returns the drone_uuid of that drone or None if no drone is waiting.
    """
    sql_query = """
    SELECT R.drone_uuid
    FROM Resources R
    JOIN ResourceStates RS ON R.state_id = RS.state_id
    WHERE RS.state = 'BootingState'
    AND R.remote_resource_uuid IS NULL
    AND R.shutdown_time IS NULL
    ORDER BY R.created, R.id
    LIMIT 1"""
    waiting_drones = await sql_registry.async_execute(sql_query, {})
    if not waiting_drones:
        return None
    drone_uuid = waiting_drones[0]["drone_uuid"]

    sql_query = """
    UPDATE Resources
    SET shutdown_time = :shutdown_time
    WHERE drone_uuid = :drone_uuid AND shutdown_time IS NULL"""
    await sql_registry.async_execute(
        sql_query, dict(drone_uuid=drone_uuid, shutdown_time=shutdown_time)
    )
    return drone_uuid
