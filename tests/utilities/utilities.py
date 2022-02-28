from tardis.interfaces.simulator import Simulator
from tardis.utilities.attributedict import AttributeDict

from unittest.mock import Mock
import asyncio
import socket


def assert_awaited_once(mock: Mock):
    if asyncio.iscoroutinefunction(mock):
        return mock.assert_awaited_once()
    else:
        return mock.assert_called_once()


def assert_awaited_with(mock: Mock, *args, **kwargs):
    if asyncio.iscoroutinefunction(mock):
        return mock.assert_awaited_with(*args, **kwargs)
    else:
        return mock.assert_called_with(*args, **kwargs)


def async_return(*args, return_value=None, **kwargs):
    loop = asyncio.get_event_loop_policy().get_event_loop()
    f = loop.create_future()
    f.set_result(return_value)
    return f


def get_free_port():  # from https://gist.github.com/dbrgn/3979133
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class MockedSimulator(Simulator):
    def __init__(self, return_value):
        self._return_value = return_value

    def get_value(self) -> float:
        return self._return_value


def mock_executor_run_command(stdout, stderr="", exit_code=0, raise_exception=None):
    def decorator(func):
        def wrapper(self):
            executor = self.mock_executor.return_value
            return_value = AttributeDict(
                stdout=stdout, stderr=stderr, exit_code=exit_code
            )
            if asyncio.iscoroutinefunction(
                executor.run_command
            ):  # since python 3.8, AsyncMock is returned, no need for async_return
                executor.run_command.return_value = return_value
            else:  # before python 3,8 MagicMock is returned, requires async_return
                executor.run_command.return_value = async_return(
                    return_value=return_value
                )
            executor.run_command.side_effect = raise_exception
            func(self)
            executor.run_command.side_effect = None

        return wrapper

    return decorator


def run_async(coroutine, *args, **kwargs):
    # return asyncio.run(coroutine(*args, **kwargs))
    loop = asyncio.get_event_loop_policy().get_event_loop()
    return loop.run_until_complete(coroutine(*args, **kwargs))


def set_awaitable_return_value(mocked_coroutine, return_value):
    # isinstance does not work due to inheritance
    # iswaitable, iscoroutine not because RuntimeWarning (not awaited)
    # comparing type(...) did not solve the problem as well.
    if not mocked_coroutine.__class__.__name__ == "MagicMock":
        mocked_coroutine.return_value = return_value
    else:  # pass test on Python 3.6 and 3.7
        mocked_coroutine.return_value = async_return(return_value=return_value)
