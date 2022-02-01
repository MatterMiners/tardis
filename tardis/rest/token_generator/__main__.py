from .generate_token import generate_token
import typer


def generate_token_cli():
    typer.run(generate_token)


if __name__ == "__main__":
    generate_token_cli()
