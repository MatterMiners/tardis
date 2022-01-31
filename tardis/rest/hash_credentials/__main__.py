from .hash_credentials import hash_credentials
import typer


def hash_credentials_cli():
    typer.run(hash_credentials)


if __name__ == "__main__":
    hash_credentials_cli()
