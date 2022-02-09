from typing import Optional
from typing_extensions import Protocol
from abc import ABCMeta, abstractmethod


class CommandResult(Protocol):
    stdout: str
    stderr: str
    exitcode: int


class Executor(metaclass=ABCMeta):
    @abstractmethod
    async def run_command(
        self, command: str, stdin_input: Optional[str] = None
    ) -> CommandResult:
        """
        Run ``command`` in a shell and provide the result
        """
        return NotImplemented
