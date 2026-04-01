"""
多Agent协作协调器 - 集中式协调管理

支持:
- 任务分配: 基于优先级/轮询/能力匹配
- Agent间通信: 消息传递和广播
- 团队行为: 编队/协同攻击/掩护
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskAssignmentStrategy(str, Enum):
    PRIORITY = "priority"        # 按优先级分配给最合适的Agent
    ROUND_ROBIN = "round_robin"  # 轮询分配
    CAPABILITY = "capability"    # 按能力匹配


@dataclass
class CoordinationTask:
    """协调任务"""
    task_id: str
    task_type: str                   # patrol / attack / defend / escort / gather
    target: Optional[str] = None
    position: Optional[tuple[float, float, float]] = None
    priority: int = 0
    required_agents: int = 1
    required_capabilities: list[str] = field(default_factory=list)
    assigned_agents: list[str] = field(default_factory=list)
    status: str = "pending"          # pending / in_progress / completed / failed
    created_at: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInfo:
    """协调器中的Agent信息"""
    agent_id: str
    agent_type: str
    capabilities: list[str] = field(default_factory=list)
    position: tuple[float, float, float] = (0, 0, 0)
    status: str = "idle"             # idle / busy / combat / dead
    current_task_id: Optional[str] = None


@dataclass
class AgentMessage:
    """Agent间消息"""
    sender: str
    receiver: str           # "*" 表示广播
    content: dict[str, Any] = field(default_factory=dict)
    msg_type: str = "info"  # info / request / response / alert
    timestamp: float = field(default_factory=time.time)


class AgentCoordinator:
    """多Agent协调管理器

    集中式协调器, 负责:
    1. 管理Agent注册/注销
    2. 任务创建与分配
    3. Agent间通信
    4. 团队协作策略
    """

    def __init__(
        self,
        strategy: TaskAssignmentStrategy = TaskAssignmentStrategy.PRIORITY,
        max_agents: int = 50,
        communication_range: float = 100.0,
    ):
        self.strategy = strategy
        self.max_agents = max_agents
        self.communication_range = communication_range

        self._agents: dict[str, AgentInfo] = {}
        self._tasks: dict[str, CoordinationTask] = {}
        self._message_queues: dict[str, deque[AgentMessage]] = {}
        self._task_counter = 0

    # ---- Agent管理 ----

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: list[str] | None = None,
        position: tuple[float, float, float] = (0, 0, 0),
    ) -> bool:
        """注册Agent"""
        if len(self._agents) >= self.max_agents:
            return False
        self._agents[agent_id] = AgentInfo(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or [],
            position=position,
        )
        self._message_queues[agent_id] = deque(maxlen=100)
        return True

    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self._agents:
            # 释放其任务
            info = self._agents[agent_id]
            if info.current_task_id and info.current_task_id in self._tasks:
                task = self._tasks[info.current_task_id]
                if agent_id in task.assigned_agents:
                    task.assigned_agents.remove(agent_id)
            del self._agents[agent_id]
            self._message_queues.pop(agent_id, None)

    def update_agent_status(
        self,
        agent_id: str,
        status: str | None = None,
        position: tuple[float, float, float] | None = None,
    ):
        """更新Agent状态"""
        if agent_id in self._agents:
            if status:
                self._agents[agent_id].status = status
            if position:
                self._agents[agent_id].position = position

    # ---- 任务管理 ----

    def create_task(
        self,
        task_type: str,
        target: str | None = None,
        position: tuple[float, float, float] | None = None,
        priority: int = 0,
        required_agents: int = 1,
        required_capabilities: list[str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> str:
        """创建协调任务"""
        self._task_counter += 1
        task_id = f"ctask_{self._task_counter}"
        task = CoordinationTask(
            task_id=task_id,
            task_type=task_type,
            target=target,
            position=position,
            priority=priority,
            required_agents=required_agents,
            required_capabilities=required_capabilities or [],
            data=data or {},
        )
        self._tasks[task_id] = task
        return task_id

    def assign_tasks(self) -> dict[str, list[str]]:
        """执行任务分配, 返回 {task_id: [agent_ids]}"""
        pending = [t for t in self._tasks.values() if t.status == "pending"]
        pending.sort(key=lambda t: t.priority, reverse=True)

        assignments = {}
        for task in pending:
            agents = self._find_agents_for_task(task)
            if len(agents) >= task.required_agents:
                selected = agents[:task.required_agents]
                task.assigned_agents = [a.agent_id for a in selected]
                task.status = "in_progress"
                for agent in selected:
                    agent.current_task_id = task.task_id
                    agent.status = "busy"
                assignments[task.task_id] = task.assigned_agents
        return assignments

    def complete_task(self, task_id: str, success: bool = True):
        """标记任务完成"""
        task = self._tasks.get(task_id)
        if not task:
            return
        task.status = "completed" if success else "failed"
        for agent_id in task.assigned_agents:
            if agent_id in self._agents:
                self._agents[agent_id].status = "idle"
                self._agents[agent_id].current_task_id = None

    # ---- 通信 ----

    def send_message(
        self,
        sender: str,
        receiver: str,
        content: dict[str, Any],
        msg_type: str = "info",
    ):
        """发送消息"""
        msg = AgentMessage(sender=sender, receiver=receiver, content=content, msg_type=msg_type)

        if receiver == "*":
            # 广播(范围内)
            sender_info = self._agents.get(sender)
            for aid, queue in self._message_queues.items():
                if aid != sender:
                    if sender_info and aid in self._agents:
                        dist = self._distance(sender_info.position, self._agents[aid].position)
                        if dist <= self.communication_range:
                            queue.append(msg)
                    else:
                        queue.append(msg)
        elif receiver in self._message_queues:
            self._message_queues[receiver].append(msg)

    def get_messages(self, agent_id: str) -> list[AgentMessage]:
        """获取Agent的消息"""
        queue = self._message_queues.get(agent_id)
        if not queue:
            return []
        messages = list(queue)
        queue.clear()
        return messages

    # ---- 查询 ----

    def get_idle_agents(self) -> list[AgentInfo]:
        return [a for a in self._agents.values() if a.status == "idle"]

    def get_agents_near(
        self,
        position: tuple[float, float, float],
        radius: float,
    ) -> list[AgentInfo]:
        return [
            a for a in self._agents.values()
            if self._distance(a.position, position) <= radius
        ]

    def get_task(self, task_id: str) -> CoordinationTask | None:
        return self._tasks.get(task_id)

    @property
    def stats(self) -> dict[str, Any]:
        status_counts = {}
        for a in self._agents.values():
            status_counts[a.status] = status_counts.get(a.status, 0) + 1
        task_counts = {}
        for t in self._tasks.values():
            task_counts[t.status] = task_counts.get(t.status, 0) + 1
        return {
            "total_agents": len(self._agents),
            "agent_status": status_counts,
            "total_tasks": len(self._tasks),
            "task_status": task_counts,
        }

    # ---- 内部 ----

    def _find_agents_for_task(self, task: CoordinationTask) -> list[AgentInfo]:
        """查找适合执行任务的Agent"""
        candidates = []
        for agent in self._agents.values():
            if agent.status != "idle":
                continue
            # 能力匹配
            if task.required_capabilities:
                if not all(c in agent.capabilities for c in task.required_capabilities):
                    continue
            # 距离(如果有位置)
            if task.position:
                dist = self._distance(agent.position, task.position)
            else:
                dist = 0
            candidates.append((dist, agent))

        if self.strategy == TaskAssignmentStrategy.PRIORITY:
            candidates.sort(key=lambda x: x[0])
        elif self.strategy == TaskAssignmentStrategy.ROUND_ROBIN:
            pass  # 保持注册顺序
        elif self.strategy == TaskAssignmentStrategy.CAPABILITY:
            candidates.sort(key=lambda x: len(x[1].capabilities), reverse=True)

        return [a for _, a in candidates]

    @staticmethod
    def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
        return ((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) ** 0.5
