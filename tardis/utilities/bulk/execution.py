from typing import TypeVar, Generic, Iterable, List, Tuple, Optional, Union
from typing_extensions import Protocol
import asyncio
import time
import sys


T = TypeVar("T")
R = TypeVar("R")


class BulkCommand(Protocol[T, R]):
    """Protocol of callables suitable for :py:class:`~.BulkExecution`"""

    async def __call__(self, __tasks: Tuple[T]) -> Optional[Iterable[R]]:
        ...


async def _read(queue: "asyncio.Queue[T]", max_items: int, max_age: float) -> List[T]:
    """Read at most ``max_items`` items during ``max_age`` seconds from the ``queue``"""
    results = []
    deadline = time.monotonic() + max_age
    while len(results) < max_items and time.monotonic() < deadline:
        try:
            if queue.empty():
                item = await asyncio.wait_for(queue.get(), deadline - time.monotonic())
            else:
                item = queue.get_nowait()
        except asyncio.TimeoutError:
            break
        else:
            results.append(item)
            queue.task_done()
    return results


class BulkExecution(Generic[T, R]):
    """
    Framework for queueing and executing several tasks via bulk commands

    :param command: async callable that executes several tasks
    :param size: maximum number of tasks to execute in one bulk
    :param delay: maximum age in seconds of tasks before executing them
    :param concurrent: how often the `command` may be executed at the same time

    Each :py:class:`~.BulkExecution` represents a different ``command``
    (for example, ``rm`` and ``mkdir``) collecting similar tasks (for example,
    ``rm foo`` and ``rm bar`` to ``rm foo bar``). The ``command`` is an arbitrary
    async callable and can freely decide how to handle its tasks. The
    :py:class:`~.BulkExecution` takes care of collecting individual tasks,
    partitioning them to bulks, and translating the results of bulk execution
    back to individual tasks.

    Both ``size`` and ``delay`` control how long to queue tasks at most
    before starting to execute them. The ``concurrent`` parameter controls whether
    and how many bulks may run at once; when concurrency is low or disabled, tasks
    may be waiting for execution even past ``size`` and ``delay``.
    Possible values for ``concurrent`` are
    :py:data:`False` (no concurrency, only one ``command`` at once),
    either of :py:data:`True` or :py:data:`None` (unlimited concurrency),
    or an integer above 0 to set a precise concurrency limit.

    .. note::

        If the ``command`` requires additional arguments,
        wrap it via :py:func:`~functools.partial`.
    """

    def __init__(
        self,
        command: BulkCommand[T, R],
        size: int,
        delay: float,
        concurrent: Union[int, bool, None] = True,
    ):
        self._command = command
        self._size = size
        self._delay = delay
        # synchronized counter for active commands
        if concurrent is False:
            self._concurrent = asyncio.BoundedSemaphore(value=1)
        elif concurrent is None or concurrent is True:
            self._concurrent = asyncio.BoundedSemaphore(value=sys.maxsize)
        elif not isinstance(concurrent, int) or concurrent <= 0:
            raise ValueError(
                "'concurrent' must be one of True, False, None or an integer above 0"
                f", got {concurrent} instead"
            )
        else:
            self._concurrent = asyncio.Semaphore(value=concurrent)
        # queue of outstanding tasks
        self._queue_ = None
        # task handling dispatch from queue to command execution
        self._master_worker: Optional[asyncio.Task] = None

    async def execute(self, task: T) -> R:
        """Execute a ``task`` in bulk and return the result"""
        result: asyncio.Future[R] = asyncio.Future()
        await self._queue.put((task, result))
        self._ensure_worker()
        return await result

    @property
    def _queue(self) -> "asyncio.Queue[Tuple[T, asyncio.Future[R]]]":
        if self._queue_ is None:
            self._queue_ = asyncio.Queue()
        return self._queue_

    def _ensure_worker(self):
        """Ensure there is a worker to dispatch tasks for command execution"""
        if self._master_worker is None:
            self._master_worker = asyncio.create_task(self._bulk_dispatch())

    async def _bulk_dispatch(self):
        """Collect tasks into bulks and dispatch them for command execution"""
        while True:
            await asyncio.sleep(0)
            bulk = list(zip(*(await _read(self._queue, self._size, self._delay))))
            if not bulk:
                continue
            tasks, futures = bulk
            await self._concurrent.acquire()
            asyncio.create_task(self._bulk_execute(tuple(tasks), futures))

    async def _bulk_execute(
        self, tasks: Tuple[T, ...], futures: List[asyncio.Future[R]]
    ) -> None:
        """Execute several ``tasks`` in bulk and set their ``futures``' result"""
        try:
            results = await self._command(tasks)
        except Exception as task_exception:
            for future in futures:
                future.set_exception(task_exception)
        else:
            if results is None:
                results = [None] * len(futures)
            for future, result in zip(futures, results):
                future.set_result(result)
        finally:
            self._concurrent.release()
