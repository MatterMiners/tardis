from abc import ABCMeta, abstractmethod


class State(metaclass=ABCMeta):
    transition = {}

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__class__.__name__

    @classmethod
    def get_all_states(cls):
        return [subclass.__name__ for subclass in cls.__subclasses__()]

    @staticmethod
    @abstractmethod
    async def run(drone):
        return NotImplemented
