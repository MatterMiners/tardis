class AsyncRunCommandFailure(Exception):
    def __init__(self, message: str, error_code: str = None, error_message: str = None):
        self.message = message
        self.error_code = error_code
        self.error_message = error_message

    def __str__(self):
        return f"(message={self.message}, error_code={self.error_code}, error_message={self.error_message})"


class TardisAuthError(Exception):
    pass


class TardisDroneCrashed(Exception):
    pass


class TardisError(Exception):
    pass


class TardisTimeout(Exception):
    pass


class TardisQuotaExceeded(Exception):
    pass


class TardisResourceStatusUpdateFailed(Exception):
    pass
