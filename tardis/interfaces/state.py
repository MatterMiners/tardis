from typing import List, TYPE_CHECKING

from abc import ABCMeta, abstractmethod

from ..utilities.pipeline import PipelineProcessor

if TYPE_CHECKING:
    from tardis.resources.drone import Drone


class State(metaclass=ABCMeta):
    transition = {}
    processing_pipeline = []

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__class__.__name__

    @classmethod
    def get_all_states(cls) -> List[str]:
        return [subclass.__name__ for subclass in cls.__subclasses__()]

    @classmethod
    @abstractmethod
    async def run(cls, drone: "Drone"):
        return NotImplemented

    @classmethod
    async def run_processing_pipeline(cls, drone: "Drone"):
        pipeline_processor = PipelineProcessor(cls.processing_pipeline)
        return await pipeline_processor.run_pipeline(
            pipeline_input=cls.transition, drone=drone, current_state=cls
        )
