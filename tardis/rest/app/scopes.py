from enum import Enum

# All available OAuth2 scopes


class ResourceScopes(str, Enum):
    get = "resources:get"
    patch = "resources:patch"


class UserScopes(str, Enum):
    get = "user:get"
