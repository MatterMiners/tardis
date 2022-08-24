from enum import Enum

# All available OAuth2 scopes


class Resources(str, Enum):
    get = "resources:get"
    patch = "resources:patch"


class User(str, Enum):
    get = "user:get"
