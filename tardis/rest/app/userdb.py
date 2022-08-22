import sqlite3
import json
from typing import Tuple

from .crud import ADD_USER, CREATE_USERS, DELETE_USER, DUMP_USERS, GET_USER
from .security import DatabaseUser


def to_db_user(user: tuple) -> DatabaseUser:
    return DatabaseUser(
        user_name=user[0], hashed_password=user[1], scopes=json.loads(user[2])
    )


class UserDB:
    def __init__(self, path: str):
        self.path = path

    def try_create_users(self):
        try:
            self.execute(CREATE_USERS)
        except sqlite3.OperationalError as e:
            if str(e) != "table Users already exists":
                raise e

    def drop_users(self):
        self.execute("DROP TABLE Users")

    def add_user(self, user: DatabaseUser):
        try:
            _, conn = self.execute(
                ADD_USER,
                (user.user_name, user.hashed_password, json.dumps(user.scopes)),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            if str(e) == "UNIQUE constraint failed: Users.user_name":
                raise Exception("USER EXISTS") from None
            else:
                raise e

    def get_user(self, user_name: str) -> DatabaseUser:
        cur, _ = self.execute(
            GET_USER,
            [user_name],
        )
        user = cur.fetchone()

        if user is None:
            raise Exception("USER NOT FOUND") from None

        return to_db_user(user)

    def dump_users(self):
        cur, _ = self.execute(DUMP_USERS)
        return cur.fetchall()

    def delete_user(self, user_name: str):
        _, conn = self.execute(DELETE_USER, [user_name])
        conn.commit()

    def execute(
        self, sql: str, args: list = []
    ) -> Tuple[sqlite3.Cursor, sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute(sql, args)
        return cur, conn
