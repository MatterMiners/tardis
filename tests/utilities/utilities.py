import abc
import asyncio
import functools
import inspect

from typing import Any, Callable


def async_return(*args, return_value=None, **kwargs):
    f = asyncio.Future()
    f.set_result(return_value)
    return f


def run_async(coroutine, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine(*args, **kwargs))


# From https://github.com/achimnol/aiotools/blob/master/src/aiotools/context.py

class AbstractAsyncContextManager(abc.ABC):
    '''
    The base abstract interface for asynchronous context manager.
    '''

    async def __aenter__(self):
        return self  # pragma: no cover

    @abc.abstractmethod
    async def __aexit__(self, exc_type, exc_value, tb):
        return None  # pragma: no cover

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractAsyncContextManager:
            if (any('__aenter__' in B.__dict__ for B in C.__mro__) and
                    any('__aexit__' in B.__dict__ for B in C.__mro__)):
                return True
        return NotImplemented


class AsyncContextDecorator:
    '''
    Make an asynchronous context manager be used as a decorator function.
    '''

    def _recreate_cm(self):
        return self

    def __call__(self, func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            async with self._recreate_cm():
                return (await func(*args, **kwargs))
        return inner


actxdecorator = AsyncContextDecorator


class AsyncContextManager(AsyncContextDecorator, AbstractAsyncContextManager):
    '''
    Converts an async-generator function into asynchronous context manager.
    '''

    def __init__(self, func: Callable[..., Any], args, kwargs):
        if not inspect.isasyncgenfunction(func):
            raise RuntimeError('Context manager function must be '
                               'an async-generator')
        self._agen = func(*args, **kwargs)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def _recreate_cm(self):
        return self.__class__(self.func, self.args, self.kwargs)

    async def __aenter__(self):
        try:
            return (await self._agen.__anext__())
        except StopAsyncIteration:
            # The generator should yield at least once.
            raise RuntimeError("async-generator didn't yield") from None

    async def __aexit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            # This is the normal path when the context body
            # did not raise any exception.
            try:
                await self._agen.__anext__()
            except StopAsyncIteration:
                return
            else:
                # The generator has already yielded,
                # no more yields are allowed.
                raise RuntimeError("async-generator didn't stop") from None
        else:
            # The context body has raised an exception.
            if exc_value is None:
                # Ensure exc_value is a valid Exception.
                exc_value = exc_type()
            try:
                # Throw the catched exception into the generator,
                # so that it can handle as it wants.
                await self._agen.athrow(exc_type, exc_value, tb)
                # Here the generator should have finished!
                # (i.e., it should not yield again in except/finally blocks!)
                raise RuntimeError("async-generator didn't stop after athrow()")
                # NOTE for PEP-479
                #   StopAsyncIteration raised inside the context body
                #   is converted to RuntimeError.
                #   In the standard library's contextlib.py, there is
                #   an extra except clause to catch StopIteration here,
                #   but this is unnecessary now.
            except StopAsyncIteration as exc_new_value:
                return exc_new_value is not exc_value
            except RuntimeError as exc_new_value:
                # When the context body did not catch the exception, re-raise.
                if exc_new_value is exc_value:
                    return False
                # When the context body's exception handler raises
                # another chained exception, re-raise.
                if isinstance(exc_value, (StopIteration, StopAsyncIteration)):
                    if exc_new_value.__cause__ is exc_value:
                        return False
                # If this is a purely new exception, raise the new one.
                raise
            except BaseException as exc:
                if exc is not exc_value:
                    raise


def async_ctx_manager(func):
    @functools.wraps(func)
    def helper(*args, **kwargs):
        return AsyncContextManager(func, args, kwargs)
    return helper
