class CommandExecutionFailure(Exception):
    def __init__(self, message: str, exit_code: int = None, stdout: str = None, stderr: str = None):
        self.message = message
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return f"(message={self.message}, exit_code={self.exit_code}, stdout={self.stdout}, stderr= {self.stderr})"
