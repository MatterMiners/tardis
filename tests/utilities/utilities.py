from tardis.utilities.attributedict import AttributeDict
import asyncio


def async_return(*args, return_value=None, **kwargs):
    f = asyncio.Future()
    f.set_result(return_value)
    return f


def mock_executor_run_command(stdout, stderr="", exit_code=0, raise_exception=None):
    def decorator(func):
        def wrapper(self):
            executor = self.mock_executor.return_value
            executor.run_command.return_value = async_return(
                return_value=AttributeDict(
                    stdout=stdout, stderr=stderr, exit_code=exit_code
                )
            )
            executor.run_command.side_effect = raise_exception
            func(self)
            executor.run_command.side_effect = None

        return wrapper

    return decorator


def run_async(coroutine, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine(*args, **kwargs))
