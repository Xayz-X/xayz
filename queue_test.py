from xayz.queue import AsyncQueue, EventType, TaskResult
import asyncio
import time

async def worker_task(name: str, sleep: int) -> None:
    """Simulates a task with a delay."""
    start = time.time()
    await asyncio.sleep(sleep)
    end = time.time()
    print(f"✅ {name} | Started at {start:.2f}s | Finished at {end:.2f}s | Duration: {end - start:.2f}s")

# ✅ Test queue with 3 concurrent workers
q: AsyncQueue = AsyncQueue(worker_task, max_workers=3)

async def main():
    await q.start()

    print("\n🔹 TEST 1: Basic Task Execution")
    await q.add_task("Task A (3s)", sleep=3, task_id=1)
    await q.add_task("Task B (1s)", sleep=1, task_id=2)
    await q.add_task("Task C (2s)", sleep=2, task_id=3)
    
    await asyncio.sleep(5)

    print("\n🔹 TEST 2: Duplicate Task Handling")
    await q.add_task("Task D (2s)", sleep=2, task_id=3)  # Duplicate ID

    print("\n🔹 TEST 3: Overload Queue Beyond Max Workers")
    for i in range(4, 10):
        await q.add_task(f"Task {i} ({i % 3 + 1}s)", sleep=i % 3 + 1, task_id=i)

    await asyncio.sleep(10)

    print("\n🔹 TEST 4: Task Deletion Before Execution")
    await q.add_task("Task X (5s)", sleep=5, task_id=20)
    await q.delete(20)  # Delete before it runs

    print("\n🔹 TEST 5: Retrieving Task Results")
    for i in range(1, 5):
        result = q.get_result(i)
        print(f"📜 Task {i} Result: {result}")

    print("\n🔹 TEST 6: Restarting Queue and Adding More Tasks")
    await q.stop()
    await q.start()
    await q.add_task("Task Restarted (3s)", sleep=3, task_id=50)

    await asyncio.sleep(5)

    print("\n🔹 TEST 7: Edge Cases - Invalid Task ID")
    try:
        await q.add_task("Task Invalid", sleep=2, task_id=None)
    except Exception as e:
        print("❌ Invalid Task ID Error:", e)

    print("\n🔹 TEST 8: Edge Cases - Handling Large Number of Tasks")
    for i in range(100, 110):
        await q.add_task(f"Task {i}", sleep=1, task_id=i)

    await asyncio.sleep(10)

    print("\n✅ All tests completed!")


@q.before_queue
async def before_queue() -> None:
    print("🔄 Before Queue Hook Called")


@q.event(event_type=EventType.DUPLICATE_ID)
async def duplicate_task_event(task: TaskResult):
    print("🚨 Duplicate Task ID:", task.id)


@q.event(event_type=EventType.STARTED)
async def start_task(task: TaskResult):
    print(f"🚀 Task {task.id} Started")


@q.event(event_type=EventType.COMPLETED)
async def task_completed(task: TaskResult):
    print(f"✅ Task {task.id} Completed at {time.time():.2f}s")


@q.event(event_type=EventType.DELETED)
async def delete_task(task: TaskResult):
    print(f"🗑️ Task {task.id} Deleted")


if __name__ == "__main__":
    asyncio.run(main())
