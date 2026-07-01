import typer

from tardis.rest.app.database import get_user_db_engine, get_user_session_factory, init_user_db
from tardis.rest.app.user_manager import CustomUserManager

app = typer.Typer(help="TARDIS REST API user management")


@app.command()
def add(
    username: str = typer.Option(..., prompt=True, help="Username for the new user"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Password for the new user"),
    scopes: str = typer.Option(None, help="Comma-separated list of scopes (e.g., resources:get,user:get)"),
) -> None:
    scope_list = [s.strip() for s in scopes.split(",")] if scopes else []
    async def _add():
        await init_user_db()
        session_factory = get_user_session_factory()
        async with session_factory() as session:
            user_manager = CustomUserManager(session)
            try:
                user = await user_manager.create(username, password, scope_list)
                typer.echo(f"User '{user.user_name}' created successfully with scopes: {scope_list}")
            except Exception as e:
                typer.echo(f"Error creating user: {e}", err=True)
                raise typer.Exit(1)
    import asyncio
    asyncio.run(_add())


@app.command()
def list_users() -> None:
    async def _list():
        await init_user_db()
        session_factory = get_user_session_factory()
        async with session_factory() as session:
            user_manager = CustomUserManager(session)
            users = await user_manager.list_all()
            if not users:
                typer.echo("No users found.")
                return
            typer.echo("Users:")
            for user in users:
                typer.echo(f"  - {user.user_name} (scopes: {', '.join(user.scopes) if user.scopes else 'none'})")
    import asyncio
    asyncio.run(_list())


@app.command()
def delete(
    username: str = typer.Option(..., prompt=True, help="Username of the user to delete"),
) -> None:
    async def _delete():
        await init_user_db()
        session_factory = get_user_session_factory()
        async with session_factory() as session:
            user_manager = CustomUserManager(session)
            user = await user_manager.get_by_username(username)
            if not user:
                typer.echo(f"User '{username}' not found.", err=True)
                raise typer.Exit(1)
            await user_manager.delete(user)
            typer.echo(f"User '{username}' deleted successfully.")
    import asyncio
    asyncio.run(_delete())


if __name__ == "__main__":
    app()