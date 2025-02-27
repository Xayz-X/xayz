import random
import logging
import inspect
import asyncio
from typing import (
    Any,
    TypeVar,
    Generic,
    Callable,
    Awaitable,
    Coroutine
)

from .utils import TaskResult, EventType

__all__ = ("AsyncQueue",)

log: logging.Logger = logging.getLogger(__name__)

_func = Callable[..., Coroutine[Any, Any, Any]]

R = TypeVar("R")  
FT = TypeVar('FT', bound=_func)


class AsyncQueue(Generic[FT, R]):
    """An advanced async queue system with concurrency control, hooks, retries, and task tracking."""

    __slots__ = (
        "queue", "worker", "max_workers", "max_retries", "error_handler", "semaphore", "delete_after_complete",
        "_worker_signature", "_running", "_tasks_done", "_before_hooks", "_after_hooks",
        "_task_events", "_task_results", "_before_hook", "_after_hook", "_event"
    )

    def __init__(
        self,
        worker: Callable[..., Awaitable[R]],  
        max_workers: int = 3,
        max_retries: int = 3,
        delete_after_complete: bool = False,
        error_handler: Callable[[Exception], Awaitable[None]] | None = None,
    ) -> None:
        """
        An advanced async queue system with concurrency control, hooks, retries, and task tracking.
        
        Parameters
        -----------
        worker (Callable[..., Awaitable[R]]): 
            The async function to process queued tasks.
        max_workers (int, optional): 
            Maximum concurrent workers (default 3).
        max_retries (int, optional): 
            Number of retries before failing a task (default 3).
        delete_after_complete (bool):
            Whether the task to eb delete after complete or not. Defaults to False.
        error_handler (Optional[Callable[[Exception], Awaitable[None]]], optional): 
            Custom error handler function. Defaults to None.
        """
        self.queue: asyncio.PriorityQueue[tuple[int, int, TaskResult[R]]] = asyncio.PriorityQueue()
        self.worker = worker
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.error_handler = error_handler
        self.semaphore = asyncio.Semaphore(max_workers)
        self.delete_after_complete: bool = delete_after_complete
        
        # Internal attributes
        self._worker_signature: inspect.Signature = inspect.signature(worker)
        self._running = False
        self._tasks_done = 0
        self._before_hook: FT | None = None
        self._after_hook: FT | None = None
        self._task_results: list[dict[int, TaskResult[R]]] = []
        self._task_events: dict[EventType, list[Callable[[TaskResult[R]], Awaitable[None]]]] = {}
        self._event: asyncio.Event = asyncio.Event()
        
    def _gen_task_id(self) -> int:
        """Generate a unique task ID."""
        return random.randint(1000, 999999)

    @property
    def is_running(self) -> bool:
        """Check if the queue is actively processing tasks."""
        return self._running

    @property
    def size(self) -> int:
        """Returns the number of tasks currently in the queue."""
        return self.queue.qsize()

    def pause(self) -> None:
        """Pause the queue"""
        self._running = False

    def resume(self) -> None:
        """Resume the queue itreation"""
        self._running = True
        
    @property
    def done(self) -> int:
        """Returns the total number of completed tasks."""
        return self._tasks_done

    @property
    def remaining(self) -> int:
        """Returns the total remaining tasks (in queue + running)."""
        return self.queue.qsize() + (self.max_workers - self.semaphore._value)

    async def start(self) -> None:
        """Start processing the queue in the background."""
        if not self._running:
            self._running = True
            asyncio.create_task(self._process_queue()) 
            await self._fire_event(EventType.STARTED, None)  
            
    async def stop(self) -> None:
        """Gracefully stop the queue processing."""
        self._running = False
        await self._fire_event(EventType.STOPPED, None)

    async def _process_queue(self) -> None:
        """Background worker that processes tasks asynchronously."""
        while self._running:
            _, _, task = await self.queue.get()
            asyncio.create_task(self.process_task(task))
            if self.queue.empty():
                log.debug("Event pause because queue is empty.")
                self._event.clear() 
                await self._event.wait()

            
    async def process_task(self, task: TaskResult[R]) -> None:
        
        async with self.semaphore:
            task.status = EventType.RUNNING
            try:
                await self._call_loop_function("before_hook")
                
                task.result = await self.worker(*task.args, **task.kwargs)
                task.status = EventType.COMPLETED
                await self._fire_event(EventType.COMPLETED, task)

            except Exception as e:
                task.status = EventType.FAILED
                task.exception = e

                if self.error_handler:
                    await self.error_handler(e)
                else:
                    log.error(f"[Error] Task {task.id} failed: {e}", exc_info=True)

                await self._fire_event(EventType.FAILED, task)
            finally:
                self._tasks_done += 1
                task._set_end_time()
                await self._call_loop_function("after_hook")
                
                if self.delete_after_complete:
                    await self.delete(task.id)
                    
    async def add_task(
        self, *args: Any, task_id: int | None = None, priority: int = 0, **kwargs: Any
    ) -> None:
        """Add a task with dynamic arguments to the queue and return its ID."""
        try:
            self._worker_signature.bind(*args, **kwargs)
        except TypeError as e:
            raise TypeError(f"Invalid arguments for worker `{self.worker.__name__}`: {e}") from e

        task_id = task_id or self._gen_task_id()
        task: TaskResult[R] = TaskResult(task_id, args, kwargs)
        task.status = EventType.ADDED
        await self.add_task_result(priority, task=task)
        
    def get_result(self, task_id: int) -> TaskResult[R] | None:
        """Retrieve the result of a completed task using optimized inline lookup."""
        task = next(
            (task_dict.get(task_id) for task_dict in self._task_results if task_id in task_dict),
            None,  # 
        )
        return task if task else None
    
    async def add_task_result(self, priority: int,  task: TaskResult[R]) -> None:
        """Add a new task result to self._task_results."""
        t = self.get_result(task.id)
        if t:
            await self._fire_event(EventType.DUPLICATE_ID, task=t)
            return 
        
        self._task_results.append({task.id: task})
        await self.queue.put((priority, task.id, task))
        await self._fire_event(EventType.ADDED, task)
        self._event.set()
    
    async def delete(self, task_id: int) -> None:
        """Delete the entire dictionary that contains the task_id, if found."""
        for i, task_dict in enumerate(self._task_results):
            if task_id in task_dict:
                task = task_dict[task_id] 
                del self._task_results[i] 
                await self._fire_event(EventType.DELETED, task) 
                return  

    
    async def clear(self) -> None:
        """Delete all tasks and fire an event for each deleted task."""
        while self._task_results: 
            task_dict = self._task_results.pop()  
            for _, task in task_dict.items():
                await self._fire_event(EventType.DELETED, task)  

    def event(self, event_type: EventType):
        """Register an event listener."""
        def decorator(func: Callable[[TaskResult[R]], Awaitable[None]]):
            self._task_events.setdefault(event_type, []).append(func)
            return func
        return decorator

    async def _fire_event(self, event_type: EventType, task: TaskResult[R] | None) -> None:
        """Trigger an event when a task changes state."""
        if task is None:
            log.debug("Task result is None while firing event, backoff from firing the event.")
            return
        for handler in self._task_events.get(event_type, []):
            await handler(task)
            
    async def _call_loop_function(self, name: str, *args: Any, **kwargs: Any) -> None:
        coro = getattr(self, '_' + name)
        if coro is None:
            return
        await coro(*args, **kwargs)
            
    def before_queue(self, coro: FT) -> FT:
        """Register a function to run before each queued task."""
        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'Expected coroutine function, received {coro.__class__.__name__}.')

        self._before_hook = coro
        return coro

    def after_queue(self, coro: FT) -> FT:
        """A decorator that registers a coroutine to be called after the loop finishes running.
        """

        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'Expected coroutine function, received {coro.__class__.__name__}.')

        self._after_hook = coro
        return coro