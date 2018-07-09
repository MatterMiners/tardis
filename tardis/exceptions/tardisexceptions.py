class AsyncRunCommandFailure(Exception):
    def __init__(self, message: str, error_code: str = None, error_message: str = None):
        self.message = message
        self.error_code = error_code
        self.error_message = error_message

    def __str__(self):
        return "(message={}, error_code={}, error_message={})".format(self.message, self.error_code, self.error_message)


class TardisAuthError(Exception):
    pass


class TardisError(Exception):
    pass


class TardisTimeout(Exception):
    pass
