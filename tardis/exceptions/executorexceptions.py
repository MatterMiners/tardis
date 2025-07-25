class CommandExecutionFailure(Exception):
    """A command run by an executor failed"""

    def __init__(
        self,
        message: str,
        exit_code: int = None,
        stdout: str = None,
        stderr: str = None,
        stdin: str = None,
    ):
        self.message = message
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.stdin = stdin

    def __str__(self):
        return (
            f"(message={self.message}, exit_code={self.exit_code}, "
            f"stdout={self.stdout}, stderr={self.stderr}, stdin={self.stdin})"
        )


class ExecutorFailure(Exception):
    """An executor itself failed when running a command"""

    def __init__(
        self,
        description: str,
        executor: object,
    ) -> None:
        super().__init__(description)
        self.description = description
        self.executor = executor
