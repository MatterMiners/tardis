from importlib.resources import path
from turtle import st
from typing import List
import typer

from .util import hash_password
from ..app.userdb import UserDB
from ..app.security import DatabaseUser

app = typer.Typer()

"""
Sample usage:
> create-table
> add-user alice password resources:get user:get
> get-user alice
> delete-user alice
"""


@app.command()
def add_user(name: str, password: str, scopes: List[str], path: str = "users.db"):
    """
    Add a user to the database. Password gets hashed.
    """
    print(f"Adding user {name} with scopes {scopes}")
    db = UserDB(path)
    dbuser = DatabaseUser(
        user_name=name, hashed_password=hash_password(password), scopes=scopes
    )
    db.add_user(dbuser)


@app.command()
def create_db(path: str = "users.db"):
    """
    Create a database file with a Users table.
    Doesn't overwrite existing files or tables.
    """
    print("Creating db with users table")
    db = UserDB(path)
    db.try_create_users()


@app.command()
def drop_users(path: str = "users.db"):
    """
    Drop the Users table.
    """
    print("Dropping users table")
    db = UserDB(path)
    db.drop_users()


@app.command()
def dump_users(path: str = "users.db"):
    """
    Dump all users from the database.
    """
    print("Dumping users table")
    db = UserDB(path)
    for user in db.dump_users():
        print(user)


@app.command()
def get_user(user_name: str, path: str = "users.db"):
    """
    Print a user from the database.
    """
    print("Getting user")
    db = UserDB(path)
    user = db.get_user(user_name)
    print(user)


@app.command()
def delete_user(user_name: str, path: str = "users.db"):
    """
    Delete a user from the database.
    """
    print("Deleting user")
    db = UserDB(path)
    db.delete_user(user_name)


if __name__ == "__main__":
    app()
