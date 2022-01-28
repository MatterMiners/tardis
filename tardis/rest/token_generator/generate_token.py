from ..app.security import create_access_token
from ...utilities.utils import disable_logging
from cobald.daemon.core.config import load

from pathlib import Path
from typing import List
import logging
import typer


def generate_token(
    user_name: str = typer.Option(
        ..., help="User name to include in the generated token"
    ),
    scopes: List[str] = typer.Option(
        ["resources:get"], help="Security scopes associated with the generated token"
    ),
    config_file: Path = typer.Option(
        None, help="Path to the COBalD/TARDIS yaml configuration"
    ),
    secret_key: str = typer.Option(
        None, help="The secret key to generate a token"
    ),
    algorithm: str = typer.Option(None, help="The algorithm to generate a token"),
):
    if config_file:
        with disable_logging(logging.DEBUG):
            with load(str(config_file)):  # type hints of load expects a string
                access_token = create_access_token(user_name=user_name, scopes=scopes)
    elif algorithm and secret_key:
        access_token = create_access_token(
            user_name=user_name,
            scopes=scopes,
            secret_key=secret_key,
            algorithm=algorithm,
        )
    else:
        typer.secho(
            "Either a config-file or a secret-key and algorithm needs to be specified!",
            bg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(access_token)
