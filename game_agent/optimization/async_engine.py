# -*- coding: utf-8 -*-
"""
异步处理引擎 - 将耗时AI计算移至后台线程

使用asyncio + ThreadPoolExecutor实现:
- 异步AI推理(LLM调用等)
- 后台批处理
- 非阻塞决策管线
"""

from __future__ import annotations

import contextlib
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class AsyncTask:
    """异步任务"""

    task_id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: int = 0
    submitted_at: float = field(default_factory=time.time)
    result: Any = None
    error: Exception | None = None
    completed: bool = False


class AsyncEngine:
    """异步处理引擎

    将耗时计算（LLM推理、路径规划等）放入线程池后台执行,
    主线程通过Future获取结果, 不阻塞游戏帧。
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._pending: dict[str, Future] = {}
        self._completed: list[AsyncTask] = []
        self._task_counter = 0

    def submit(
        self,
        func: Callable,
        *args,
        task_id: str | None = None,
        priority: int = 0,
        **kwargs,
    ) -> str:
        """提交异步任务

        Args:
            func: 要执行的函数
            task_id: 任务ID, 为空则自动生成
            priority: 优先级

        Returns:
            任务ID
        """
        if task_id is None:
            self._task_counter += 1
            task_id = f'task_{self._task_counter}'

        future = self._executor.submit(func, *args, **kwargs)
        self._pending[task_id] = future

        def _on_done(fut: Future):
            try:
                result = fut.result()
                task = AsyncTask(
                    task_id=task_id,
                    func=func,
                    result=result,
                    completed=True,
                )
            except Exception as e:
                task = AsyncTask(
                    task_id=task_id,
                    func=func,
                    error=e,
                    completed=True,
                )
            self._completed.append(task)
            self._pending.pop(task_id, None)

        future.add_done_callback(_on_done)
        return task_id

    def get_result(self, task_id: str, timeout: float | None = None) -> Any:
        """获取任务结果(阻塞)"""
        future = self._pending.get(task_id)
        if future:
            return future.result(timeout=timeout)
        # 从已完成中查找
        for task in self._completed:
            if task.task_id == task_id:
                if task.error:
                    raise task.error
                return task.result
        raise KeyError(f"Task '{task_id}' not found")

    def try_get_result(self, task_id: str) -> tuple[bool, Any]:
        """尝试获取结果(非阻塞)

        Returns:
            (is_done, result_or_None)
        """
        future = self._pending.get(task_id)
        if future:
            if future.done():
                try:
                    return True, future.result()
                except Exception as e:
                    return True, e
            return False, None

        for task in self._completed:
            if task.task_id == task_id:
                return True, task.result
        return False, None

    def is_pending(self, task_id: str) -> bool:
        return task_id in self._pending

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    def collect_completed(self) -> list[AsyncTask]:
        """收集所有已完成的任务并清空"""
        tasks = list(self._completed)
        self._completed.clear()
        return tasks

    def shutdown(self, wait: bool = True):
        """关闭引擎"""
        self._executor.shutdown(wait=wait)

    def __del__(self):
        with contextlib.suppress(Exception):
            self._executor.shutdown(wait=False)


class AsyncBatchProcessor:
    """异步批处理器 - 将多个小任务合并为批次执行"""

    def __init__(self, engine: AsyncEngine, batch_size: int = 10, flush_interval: float = 0.5):
        self.engine = engine
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: list[tuple[Callable, tuple, dict]] = []
        self._last_flush = time.time()

    def add(self, func: Callable, *args, **kwargs):
        """添加任务到批缓冲"""
        self._buffer.append((func, args, kwargs))
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> list[str]:
        """强制提交当前缓冲"""
        if not self._buffer:
            return []

        task_ids = []
        for func, args, kwargs in self._buffer:
            tid = self.engine.submit(func, *args, **kwargs)
            task_ids.append(tid)

        self._buffer.clear()
        self._last_flush = time.time()
        return task_ids

    def maybe_flush(self) -> list[str]:
        """如果超过间隔则flush"""
        if time.time() - self._last_flush >= self.flush_interval:
            return self.flush()
        return []
