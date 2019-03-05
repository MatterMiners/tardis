from abc import ABCMeta, abstractmethod


class Executor(metaclass=ABCMeta):
    @abstractmethod
    async def run_command(self, command):
        return NotImplemented
