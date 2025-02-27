# AsyncQueue

*A powerful asynchronous queue system with concurrency control, event handling, and retries.*

> ⚡ **Why AsyncQueue?**  
> - Handles **concurrent** tasks efficiently.  
> - Supports **prioritized execution** of tasks.  
> - Offers **event-driven hooks** for better control.  
> - Implements **automatic retries** for failed tasks.  
> - Provides **graceful shutdown** to ensure safe task termination.  

---

## 📌 **Features**  

✅ **Concurrency Control** – Limits the number of active tasks.  
✅ **Task Prioritization** – Higher priority tasks run first.  
✅ **Retries** – Automatically retries failed tasks.  
✅ **Event Handling** – Trigger functions when tasks change state.  
✅ **Hooks** – Custom functions before and after each task.  
✅ **Task Tracking** – Monitor execution progress & results.  
✅ **Graceful Shutdown** – Ensures safe stopping of the queue.  

---

## 🛠 **Installation**  

Clone the repository and install dependencies:  
```sh
git clone https://github.com/Xayz-X/xayz.git
```

---

## 🚀 **Basic Usage**  

### **1 Create an AsyncQueue and Add Tasks**  

```python
import asyncio
from xayz.queue import AsyncQueue, TaskResult, EventType

async def worker(task_id: int, duration: int) -> str:
    await asyncio.sleep(duration)
    return f"Task {task_id} completed in {duration} seconds"

async def main():
    queue = AsyncQueue(worker, max_workers=3, max_retries=2)

    await queue.add_task(1, 2, priority=1)
    await queue.add_task(2, 1, priority=2)
    await queue.add_task(3, 3, priority=0)

    await queue.start()

    await asyncio.sleep(5)  # Wait for tasks to complete
    await queue.stop()

asyncio.run(main())
```

> [!WARNING]  
> Ensure `asyncio.run(main())` is **only used in scripts**. Inside another `async` function, use `await main()` instead.

---

## 🔥 **Event Handling**  

Register event handlers for different task events:  

```python
@queue.event(EventType.COMPLETED)
async def on_task_completed(task: TaskResult):
    print(f"✅ Task {task.id} completed with result: {task.result}")

@queue.event(EventType.FAILED)
async def on_task_failed(task: TaskResult):
    print(f"❌ Task {task.id} failed with exception: {task.exception}")
```

### **📝 Supported Events**
| Event Type        | Description |
|------------------|------------|
| `task_added`     | Triggered when a task is added |
| `task_started`   | Fired when a task begins execution |
| `task_completed` | Called when a task completes successfully |
| `task_failed`    | Fired if a task encounters an error |
| `duplicate_task_id` | Triggered if a duplicate task ID is detected |
| `task_deleted`   | Fired when a task is removed |

> [!INFO]  
> Event handlers are **optional** but useful for **logging, analytics, and debugging**.

---

## 🎯 **Task Prioritization**  
Higher priority tasks **execute first**. Priority **0** is the lowest.  

```python
await queue.add_task(1, 2, priority=1)  # Medium priority
await queue.add_task(2, 1, priority=2)  # High priority
await queue.add_task(3, 3, priority=0)  # Low priority
```

> [!WARNING]
> If two tasks have the **same priority**, they run **in order of submission**.

---

## 🔄 **Retries**  
Failed tasks are **automatically retried**.  

```python
queue = AsyncQueue(worker, max_retries=3)  # Retries up to 3 times
```

> [!TIP]
> Set **max_retries** based on how frequently failures are expected.

---

## 🛠 **Hooks (Before & After Task Execution)**  
Run custom functions **before** or **after** each task.  

```python
@queue.before_queue
async def before_task(*args, **kwargs):
    print("🟡 Before task execution")

@queue.after_queue
async def after_task(*args, **kwargs):
    print("🟢 After task execution")
```

> [!INFO]
> Hooks **do not affect** task execution but can be useful for **logging, metrics, or setup tasks**.

---

## 😫 **Graceful Shutdown**  
Ensures all tasks finish **before stopping** the queue.  

```python
await queue.stop()
```

> [!WARNING]  
> Always stop the queue **before exiting** to prevent lost tasks.

