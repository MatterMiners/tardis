import bcrypt
import typer


def hash_credentials(
    password: str = typer.Argument(..., help="Password to hash with bcrypt")
):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt)
    typer.echo(hashed_password)
