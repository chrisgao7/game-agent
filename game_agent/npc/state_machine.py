"""
状态机(FSM) - NPC高层状态管理

与行为树配合使用:
- 状态机管理高级状态(巡逻/警戒/战斗/交互)
- 每个状态可绑定一棵行为树, 处理该状态下的具体行为逻辑
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from game_agent.npc.behavior_tree import BehaviorTree, BehaviorStatus


@dataclass
class Transition:
    """状态转移规则"""
    from_state: str
    to_state: str
    condition: Callable[[dict[str, Any]], bool]
    priority: int = 0
    cooldown: float = 0.0
    _last_trigger: float = 0.0

    def can_trigger(self, context: dict[str, Any]) -> bool:
        if self.cooldown > 0:
            if time.time() - self._last_trigger < self.cooldown:
                return False
        try:
            return self.condition(context)
        except Exception:
            return False

    def trigger(self):
        self._last_trigger = time.time()


class State:
    """状态节点

    每个状态包含:
    - 进入/退出回调
    - 可选的行为树(处理该状态下的细粒度行为)
    - 更新逻辑
    """

    def __init__(
        self,
        name: str,
        behavior_tree: BehaviorTree | None = None,
        on_enter: Callable[[dict[str, Any]], None] | None = None,
        on_exit: Callable[[dict[str, Any]], None] | None = None,
        on_update: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.name = name
        self.behavior_tree = behavior_tree
        self._on_enter = on_enter
        self._on_exit = on_exit
        self._on_update = on_update
        self.enter_time: float = 0.0

    def enter(self, context: dict[str, Any]):
        self.enter_time = time.time()
        if self._on_enter:
            self._on_enter(context)

    def exit(self, context: dict[str, Any]):
        if self._on_exit:
            self._on_exit(context)

    def update(self, context: dict[str, Any]) -> BehaviorStatus:
        """更新状态, 如果绑定了行为树则执行行为树"""
        if self._on_update:
            self._on_update(context)

        if self.behavior_tree:
            return self.behavior_tree.tick(context)
        return BehaviorStatus.SUCCESS

    @property
    def elapsed(self) -> float:
        """在当前状态停留的时间"""
        return time.time() - self.enter_time


class StateMachine:
    """有限状态机

    管理NPC的高层行为状态, 支持:
    - 条件触发的状态转移
    - 优先级排序
    - 冷却时间
    - 与行为树集成
    """

    def __init__(self, name: str = "default_fsm"):
        self.name = name
        self._states: dict[str, State] = {}
        self._transitions: list[Transition] = []
        self._current_state: Optional[State] = None
        self._history: list[str] = []
        self._max_history = 50

    @property
    def current_state(self) -> str | None:
        return self._current_state.name if self._current_state else None

    def add_state(self, state: State) -> StateMachine:
        self._states[state.name] = state
        return self

    def add_transition(self, transition: Transition) -> StateMachine:
        self._transitions.append(transition)
        # 按优先级排序
        self._transitions.sort(key=lambda t: t.priority, reverse=True)
        return self

    def set_initial_state(self, state_name: str, context: dict[str, Any] | None = None):
        """设置初始状态"""
        if state_name not in self._states:
            raise ValueError(f"State '{state_name}' not found")
        self._current_state = self._states[state_name]
        self._current_state.enter(context or {})
        self._history.append(state_name)

    def update(self, context: dict[str, Any]) -> BehaviorStatus:
        """更新状态机

        1. 检查是否有满足条件的状态转移
        2. 如果有, 执行转移
        3. 更新当前状态(执行其行为树)
        """
        if self._current_state is None:
            return BehaviorStatus.FAILURE

        # 检查转移
        for transition in self._transitions:
            if transition.from_state != self._current_state.name:
                continue
            if transition.can_trigger(context):
                self._do_transition(transition, context)
                break

        # 更新当前状态
        return self._current_state.update(context)

    def force_transition(self, target_state: str, context: dict[str, Any] | None = None):
        """强制转移到指定状态"""
        if target_state not in self._states:
            raise ValueError(f"State '{target_state}' not found")
        ctx = context or {}
        if self._current_state:
            self._current_state.exit(ctx)
        self._current_state = self._states[target_state]
        self._current_state.enter(ctx)
        self._history.append(target_state)
        self._trim_history()

    def get_history(self) -> list[str]:
        return list(self._history)

    def _do_transition(self, transition: Transition, context: dict[str, Any]):
        target = self._states.get(transition.to_state)
        if not target:
            return

        transition.trigger()
        if self._current_state:
            self._current_state.exit(context)

        self._current_state = target
        self._current_state.enter(context)
        self._history.append(transition.to_state)
        self._trim_history()

    def _trim_history(self):
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "current_state": self.current_state,
            "states": list(self._states.keys()),
            "transitions": len(self._transitions),
            "history_length": len(self._history),
        }
