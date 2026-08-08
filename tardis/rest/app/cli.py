import asyncio
from contextlib import asynccontextmanager
from functools import wraps

import typer
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tardis.rest.app.models import Base
from tardis.rest.app.user_manager import CustomUserManager

app = typer.Typer(help="TARDIS REST API user management")


def coro(f):
    """Decorator to run async functions within Typer commands."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@asynccontextmanager
async def get_user_session(db_url: str):
    """Async context manager to handle engine creation, session yields, and teardown."""
    engine = create_async_engine(db_url, echo=False)

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            yield session
    finally:
        # Guarantee the engine is disposed of before the CLI exits
        await engine.dispose()


@app.callback()
def main_callback(
    ctx: typer.Context,
    user_db_url: str = typer.Option(
        ..., help="SQLAlchemy database URL for user storage"
    ),
):
    """Callback to store global CLI options."""
    ctx.ensure_object(dict)
    ctx.obj["user_db_url"] = user_db_url


@app.command()
@coro
async def add(
    ctx: typer.Context,
    username: str = typer.Option(..., prompt=True, help="Username for the new user"),
    password: str = typer.Option(
        ..., prompt=True, hide_input=True, help="Password for the new user"
    ),
    scopes: str = typer.Option(
        None, help="Comma-separated list of scopes (e.g., resources:get,user:get)"
    ),
) -> None:
    db_url = ctx.obj["user_db_url"]
    scope_list = [s.strip() for s in scopes.split(",")] if scopes else []

    async with get_user_session(db_url) as session:
        user_manager = CustomUserManager(session)
        try:
            user = await user_manager.create(username, password, scope_list)
            typer.echo(
                f"User '{user.user_name}' created successfully with scopes: {scope_list}"  # noqa: B950
            )
        except Exception as err:
            typer.echo(f"Error creating user: {err}", err=True)
            raise typer.Exit(1) from err


@app.command()
@coro
async def list_users(ctx: typer.Context) -> None:
    db_url = ctx.obj["user_db_url"]

    async with get_user_session(db_url) as session:
        user_manager = CustomUserManager(session)
        users = await user_manager.list_all()

        if not users:
            typer.echo("No users found.")
            return

        typer.echo("Users:")
        for user in users:
            scopes_str = ", ".join(user.scopes) if user.scopes else "none"
            typer.echo(f"  - {user.user_name} (scopes: {scopes_str})")


@app.command()
@coro
async def delete(
    ctx: typer.Context,
    username: str = typer.Option(
        ..., prompt=True, help="Username of the user to delete"
    ),
) -> None:
    db_url = ctx.obj["user_db_url"]

    async with get_user_session(db_url) as session:
        user_manager = CustomUserManager(session)
        user = await user_manager.get_by_username(username)

        if not user:
            typer.echo(f"User '{username}' not found.", err=True)
            raise typer.Exit(1)

        await user_manager.delete(user)
        typer.echo(f"User '{username}' deleted successfully.")


if __name__ == "__main__":
    app()
