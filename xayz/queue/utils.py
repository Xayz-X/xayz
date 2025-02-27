from datetime import datetime as dt
from datetime import timezone as tz
from enum import Enum
from typing import TypeVar, Generic, Any

__all__: tuple[str, ...] = ("EventType", "TaskResult")

R = TypeVar("R")  

class EventType(Enum):
    """
    Enum representing different states of a queued task.
    
    Parameters
    ------------
        START (str): 
            Indicates that the task has started for the first time.
        COMPLETED (str): 
            Indicates that the task has been completed.
        FAILED (str): 
            Indicates that the task has failed.
        CANCELLED (str): 
            Indicates that the task has been cancelled.
        RUNNING (str): 
            Indicates that the task is currently running.
        STOPPED (str): 
            Indicates that the task has been stopped.
    """
    ADDED ="task_added"
    STARTED = "task_started"
    COMPLETED = "task_completed"
    FAILED = "task_failed"
    CANCELLED = "task_cancelled"
    RUNNING = "task_running"
    STOPPED = "task_stopped"
    DUPLICATE_ID = "duplicate_task_id"
    DELETED = "task_deleted"
    
    
class TaskResult(Generic[R]):
    """
    Represents a queued task with its execution status and result.
    
    Parameters
    ------------
        id `(int)`: 
            The unique identifier for the task.
        name (str): 
            The name of the task, formatted as "Task-{task_id}".
        args `(tuple[Any, ...])`:    
            The positional arguments passed to the task.
        kwargs `(dict[str, Any])`: 
            The keyword arguments passed to the task.
        status `(EventType)`: 
            The current execution status of the task.
        result `(R | None)`: 
            The result of the task execution, if any.
        exception `(Exception | None)`:   
            The exception raised during task execution, if any.
        started `(dt)`:
            When the task has been started.
        ended `(dt | None)`:
            When the task has been ended.    
    """
    
    def __init__(self, task_id: int, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.id = task_id
        self.name = f"Task-{task_id}"
        self.args = args
        self.kwargs = kwargs
        self.status: EventType = EventType.RUNNING
        self.result: R | None = None
        self.exception: Exception | None = None
        self.start_time: dt = dt.now(tz.utc) # utc timezone
        self.end_time: dt | None = None
        
    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status.value} result={self.result}>"
    
    def _set_end_time(self) -> None:
        """Sets the end time of the task to now (UTC) or a given value."""
        self.end_time = dt.now(tz.utc) 