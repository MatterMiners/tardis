from functools import cached_property
from typing import TypeVar, Generic, Iterable, List, Tuple, Optional, Set
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


class AsyncBulkCall(Generic[T, R]):
    """
    Framework for queueing and executing several tasks via bulk commands

    :param command: async callable that executes several tasks
    :param size: maximum number of tasks to execute in one bulk
    :param delay: maximum time window for tasks to execute in one bulk
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
    before starting to execute them. The ``concurrent`` parameter controls
    how many bulks may run at once; when concurrency is low tasks
    may be waiting for execution even past ``size`` and ``delay``.
    Possible values for ``concurrent`` are :py:data:`None` for unlimited concurrency
    or an integer above 0 to set a precise concurrency limit.

    .. note::

        If the ``command`` requires additional arguments,
        wrap it via :py:func:`~functools.partial`, for example
        ``AsyncBulkCall(partial(async_rm, force=True), ...)``.
    """

    def __init__(
        self,
        command: BulkCommand[T, R],
        size: int,
        delay: float,
        concurrent: Optional[int] = None,
    ):
        self._command = command
        self._size = size
        self._delay = delay
        self._concurrency = sys.maxsize if concurrent is None else concurrent
        # task handling dispatch from queue to command execution
        self._dispatch_task: Optional[asyncio.Task] = None
        # tasks handling individual command executions
        self._bulk_tasks: Set[asyncio.Task] = set()
        self._verify_settings()

    @cached_property
    def _concurrent(self) -> "asyncio.BoundedSemaphore":
        """synchronized counter for active commands"""
        return asyncio.BoundedSemaphore(value=self._concurrency)

    @cached_property
    def _queue(self) -> "asyncio.Queue[Tuple[T, asyncio.Future[R]]]":
        """queue of outstanding tasks"""
        return asyncio.Queue()

    def _verify_settings(self):
        if not isinstance(self._size, int) or self._size <= 0:
            raise ValueError(f"expected 'size' > 0, got {self._size!r} instead")
        if self._delay <= 0:
            raise ValueError(f"expected 'delay' > 0, got {self._delay!r} instead")
        if not isinstance(self._concurrency, int) or self._concurrency <= 0:
            raise ValueError(
                "'concurrent' must be None or an integer above 0"
                f", got {self._concurrency!r} instead"
            )

    async def __call__(self, __task: T) -> R:
        """Queue a ``task`` for bulk execution and return the result when available"""
        result: "asyncio.Future[R]" = asyncio.get_event_loop().create_future()
        # queue item first so that the dispatch task does not finish before
        self._queue.put_nowait((__task, result))
        # ensure there is a worker to dispatch items for command execution
        if self._dispatch_task is None:
            self._dispatch_task = asyncio.ensure_future(self._bulk_dispatch())
        return await result

    async def _bulk_dispatch(self):
        """Collect tasks into bulks and dispatch them for command execution"""
        while not self._queue.empty():
            bulk = list(zip(*(await self._get_bulk())))  # noqa B905
            if not bulk:
                continue
            tasks, futures = bulk
            # limit concurrent bulk execution
            # We must make sure *here* that a new bulk can be launched, but
            # we must release the claim *in the task* when it is done.
            await self._concurrent.acquire()
            task = asyncio.ensure_future(self._bulk_execute(tuple(tasks), futures))
            task.add_done_callback(lambda _: self._concurrent.release)
            # track tasks via strong references to avoid them being garbage collected.
            # see bpo#44665
            self._bulk_tasks.add(task)
            task.add_done_callback(lambda _, task=task: self._bulk_tasks.discard(task))
            # yield to the event loop so that the `while True` loop does not arbitrarily
            # delay other tasks on the fast paths for `_get_bulk` and `acquire`.
            await asyncio.sleep(0)
        self._dispatch_task = None

    async def _get_bulk(self) -> "List[Tuple[T, asyncio.Future[R]]]":
        """Fetch the next bulk from the internal queue"""
        max_items, queue = self._size, self._queue
        # always pull in at least one item asynchronously
        # this avoids stalling for very low delays and efficiently waits for items
        results = [await queue.get()]
        queue.task_done()
        deadline = time.monotonic() + self._delay
        while len(results) < max_items and time.monotonic() < deadline:
            try:
                if queue.empty():
                    item = await asyncio.wait_for(
                        queue.get(), deadline - time.monotonic()
                    )
                else:
                    item = queue.get_nowait()
            except asyncio.TimeoutError:
                break
            else:
                results.append(item)
                queue.task_done()
        return results

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
            for future, result in zip(futures, results):  # noqa B905
                future.set_result(result)
