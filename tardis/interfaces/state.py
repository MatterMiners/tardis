from ..utilities.pipeline import PipelineProcessor
from ..utilities.pipeline import StopProcessing

from abc import ABCMeta, abstractmethod


class State(metaclass=ABCMeta):
    transition = {}
    processing_pipeline = []

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__class__.__name__

    @classmethod
    def get_all_states(cls):
        return [subclass.__name__ for subclass in cls.__subclasses__()]

    @classmethod
    @abstractmethod
    async def run(cls, drone):
        return NotImplemented

    @classmethod
    async def run_processing_pipeline(cls, drone):
        try:
            pipeline_processor = PipelineProcessor(cls.processing_pipeline)
            return await pipeline_processor.run_pipeline(pipeline_input=cls.transition, drone=drone, current_state=cls)
        except StopProcessing as ex:
            return ex.last_result
