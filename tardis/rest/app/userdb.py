import sqlite3
import json

from .crud import ADD_USER, CREATE_USERS, DELETE_USER, GET_USER
from .security import DatabaseUser


def to_db_user(user: tuple) -> DatabaseUser:
    return DatabaseUser(
        user_name=user[0], hashed_password=user[1], scopes=json.loads(user[2])
    )


class UserDB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.cur = self.conn.cursor()

    def try_create_users(self):
        try:
            self.cur.execute(CREATE_USERS)
        except sqlite3.OperationalError as e:
            if str(e) != "table Users already exists":
                raise e

    def drop_users(self):
        self.conn.execute("DROP TABLE Users")

    def add_user(self, user: DatabaseUser):
        try:
            self.cur.execute(
                ADD_USER,
                (user.user_name, user.hashed_password, json.dumps(user.scopes)),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            if str(e) == "UNIQUE constraint failed: Users.user_name":
                raise Exception("USER EXISTS") from None
            else:
                raise e

    def get_user(self, user_name: str) -> DatabaseUser:
        self.cur.execute(
            GET_USER,
            [user_name],
        )
        user = self.cur.fetchone()

        if user is None:
            raise Exception("USER NOT FOUND") from None

        return to_db_user(user)

    def dump_users(self):
        self.cur.execute("SELECT user_name, hashed_password, scopes FROM Users")
        return self.cur.fetchall()

    def delete_user(self, user_name: str):
        self.cur.execute(DELETE_USER, [user_name])
        self.conn.commit()
