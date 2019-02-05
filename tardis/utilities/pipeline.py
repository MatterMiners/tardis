import asyncio


class StopProcessing(BaseException):
    def __init__(self, last_result):
        self._last_result = last_result

    @property
    def last_result(self):
        return self._last_result


class PipelineProcessor(object):
    def __init__(self, pipeline=None):
        self._processing_pipeline = pipeline or []

    def add_to_pipeline(self, func):
        if callable(func):
            self._processing_pipeline.append(func)

    async def run_pipeline(self, pipeline_input, *args, **kwargs):
        try:
            pipeline = asyncio.Future()
            pipeline.set_result(pipeline_input)

            for func_call in self._processing_pipeline:
                pipeline = func_call(await pipeline, *args, **kwargs)
            return await pipeline
        except StopProcessing as ex:
            return ex.last_result
