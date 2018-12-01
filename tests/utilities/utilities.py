import asyncio


def async_return(result):
    f = asyncio.Future()
    f.set_result(result)
    return f


def run_async(coroutine, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine(*args, **kwargs))
