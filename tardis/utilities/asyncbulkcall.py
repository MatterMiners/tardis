from typing import TypeVar, Generic, Iterable, List, Tuple, Optional, Union
from typing_extensions import Protocol
import asyncio
import time
import sys


T = TypeVar("T")
R = TypeVar("R")


class BulkCommand(Protocol[T, R]):
    """
    Protocol of callables suitable for :py:class:`~.BulkExecution`

    A bulk command must take an arbitrary number of tasks and is expected to provide
    an iterable of one result per task. Alternatively, it may provide a single
    :py:data:`None` value to indicate that there is no result. An unhandled
    :py:class:`Exception` means that all tasks failed with that :py:class:`Exception`.
    """

    async def __call__(self, *__tasks: T) -> Optional[Iterable[R]]:
        ...


async def _read(queue: "asyncio.Queue[T]", max_items: int, max_age: float) -> List[T]:
    """Read at most ``max_items`` items during ``max_age`` seconds from the ``queue``"""
    results = []
    deadline = time.monotonic() + max_age
    while len(results) < max_items:
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
        # check deadline late so that we cannot stall if the delay is very low
        if time.monotonic() > deadline:
            break
    return results


class AsyncBulkCall(Generic[T, R]):
    """
    Framework for queueing and executing several tasks via bulk commands

    :param command: async callable that executes several tasks
    :param size: maximum number of tasks to execute in one bulk
    :param delay: maximum age in seconds of tasks before executing them
    :param concurrent: how often the `command` may be executed at the same time

    Given some bulk-task callable ``(T, ...) -> (R, ...)`` (the ``command``),
    :py:class:`~.BulkExecution` represents a single-task callable ``(T) -> R``.
    Single-task calls are buffered for a moment according to ``size`` and ``delay``,
    then executed in bulk with ``concurrent`` calls to ``command``.

    Each :py:class:`~.BulkExecution` should represent a different ``command``
    (for example, ``rm`` or ``mkdir``) collecting similar tasks (for example,
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
        self._concurrent_ = None
        self._concurrency = (
            1
            if concurrent is False
            else sys.maxsize
            if concurrent is None or concurrent is True
            else concurrent
        )
        # queue of outstanding tasks
        self._queue_ = None
        # task handling dispatch from queue to command execution
        self._master_worker: Optional[asyncio.Task] = None
        self._verify_settings()

    def _verify_settings(self):
        if not isinstance(self._size, int) or self._size <= 0:
            raise ValueError(f"expected 'size' > 0, got {self._size!r} instead")
        if self._delay <= 0:
            raise ValueError(f"expected 'delay' > 0, got {self._delay!r} instead")
        if not isinstance(self._concurrency, int) or self._concurrency <= 0:
            raise ValueError(
                "'concurrent' must be one of True, False, None or an integer above 0"
                f", got {self._concurrency!r} instead"
            )

    async def __call__(self, __task: T) -> R:
        """Execute a ``task`` in bulk and return the result"""
        result: "asyncio.Future[R]" = asyncio.Future()
        await self._queue.put((__task, result))
        self._ensure_worker()
        return await result

    @property
    def _concurrent(self) -> "asyncio.BoundedSemaphore":
        if self._concurrent_ is None:
            self._concurrent_ = asyncio.BoundedSemaphore(value=self._concurrency)
        return self._concurrent_

    @property
    def _queue(self) -> "asyncio.Queue[Tuple[T, asyncio.Future[R]]]":
        if self._queue_ is None:
            self._queue_ = asyncio.Queue()
        return self._queue_

    def _ensure_worker(self):
        """Ensure there is a worker to dispatch tasks for command execution"""
        if self._master_worker is None:
            self._master_worker = asyncio.ensure_future(self._bulk_dispatch())

    async def _bulk_dispatch(self):
        """Collect tasks into bulks and dispatch them for command execution"""
        while True:
            await asyncio.sleep(0)
            bulk = list(zip(*(await _read(self._queue, self._size, self._delay))))
            if not bulk:
                continue
            tasks, futures = bulk
            await self._concurrent.acquire()
            asyncio.ensure_future(self._bulk_execute(tuple(tasks), futures))

    async def _bulk_execute(
        self, tasks: Tuple[T, ...], futures: "List[asyncio.Future[R]]"
    ) -> None:
        """Execute several ``tasks`` in bulk and set their ``futures``' result"""
        try:
            results = await self._command(*tasks)
            # make sure we can cleanly match input to output
            results = [None] * len(futures) if results is None else list(results)
            if len(results) != len(futures):
                raise RuntimeError(
                    f"bulk command {self._command} provided {len(results)} results"
                    f", expected {len(futures)} results or 'None'"
                )
        except Exception as task_exception:
            for future in futures:
                future.set_exception(task_exception)
        else:
            for future, result in zip(futures, results):
                future.set_result(result)
        finally:
            self._concurrent.release()
