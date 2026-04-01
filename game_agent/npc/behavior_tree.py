# -*- coding: utf-8 -*-
"""
行为树(Behavior Tree) - 灵活的NPC行为决策逻辑

节点类型:
- SelectorNode: 选择器 - 执行第一个成功的子节点
- SequenceNode: 序列 - 按顺序执行所有子节点
- ConditionNode: 条件判断
- ActionNode: 叶子节点, 执行具体动作
- DecoratorNode: 装饰器 - 修改子节点行为(反转/重复等)
"""

from __future__ import annotations

import time
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class BehaviorStatus(str, Enum):
    SUCCESS = 'success'
    FAILURE = 'failure'
    RUNNING = 'running'


class BehaviorNode:
    """行为树节点基类"""

    def __init__(self, name: str = ''):
        self.name = name
        self.parent: BehaviorNode | None = None
        self.status: BehaviorStatus = BehaviorStatus.FAILURE

    def tick(self, context: dict[str, Any]) -> BehaviorStatus:
        """执行节点逻辑"""
        raise NotImplementedError

    def reset(self):
        self.status = BehaviorStatus.FAILURE

    def __repr__(self):
        return f'{self.__class__.__name__}({self.name})'


class CompositeNode(BehaviorNode):
    """组合节点基类"""

    def __init__(self, name: str = '', children: list[BehaviorNode] | None = None):
        super().__init__(name)
        self.children: list[BehaviorNode] = children or []
        for child in self.children:
            child.parent = self

    def add_child(self, child: BehaviorNode) -> CompositeNode:
        child.parent = self
        self.children.append(child)
        return self

    def reset(self):
        super().reset()
        for child in self.children:
            child.reset()


class SelectorNode(CompositeNode):
    """选择器节点 - 依次尝试子节点, 返回第一个成功的结果

    逻辑: OR - 任一成功即成功, 全部失败才失败
    """

    def tick(self, context: dict[str, Any]) -> BehaviorStatus:
        for child in self.children:
            status = child.tick(context)
            if status != BehaviorStatus.FAILURE:
                self.status = status
                return status
        self.status = BehaviorStatus.FAILURE
        return BehaviorStatus.FAILURE


class SequenceNode(CompositeNode):
    """序列节点 - 依次执行所有子节点, 全部成功才成功

    逻辑: AND - 全部成功才成功, 任一失败即失败
    """

    def __init__(self, name: str = '', children: list[BehaviorNode] | None = None):
        super().__init__(name, children)
        self._current_index = 0

    def tick(self, context: dict[str, Any]) -> BehaviorStatus:
        while self._current_index < len(self.children):
            child = self.children[self._current_index]
            status = child.tick(context)

            if status == BehaviorStatus.RUNNING:
                self.status = BehaviorStatus.RUNNING
                return BehaviorStatus.RUNNING
            elif status == BehaviorStatus.FAILURE:
                self._current_index = 0
                self.status = BehaviorStatus.FAILURE
                return BehaviorStatus.FAILURE

            self._current_index += 1

        self._current_index = 0
        self.status = BehaviorStatus.SUCCESS
        return BehaviorStatus.SUCCESS

    def reset(self):
        super().reset()
        self._current_index = 0


class ConditionNode(BehaviorNode):
    """条件节点 - 判断条件是否满足"""

    def __init__(self, name: str, condition: Callable[[dict[str, Any]], bool]):
        super().__init__(name)
        self.condition = condition

    def tick(self, context: dict[str, Any]) -> BehaviorStatus:
        try:
            result = self.condition(context)
            self.status = BehaviorStatus.SUCCESS if result else BehaviorStatus.FAILURE
        except Exception:
            self.status = BehaviorStatus.FAILURE
        return self.status


class ActionNode(BehaviorNode):
    """动作节点 - 执行具体行为"""

    def __init__(
        self,
        name: str,
        action: Callable[[dict[str, Any]], BehaviorStatus],
    ):
        super().__init__(name)
        self.action = action

    def tick(self, context: dict[str, Any]) -> BehaviorStatus:
        try:
            self.status = self.action(context)
        except Exception:
            self.status = BehaviorStatus.FAILURE
        return self.status


class DecoratorNode(BehaviorNode):
    """装饰器节点基类 - 修改单个子节点的行为"""

    def __init__(self, name: str, child: BehaviorNode):
        super().__init__(name)
        self.child = child
        self.child.parent = self

    def reset(self):
        super().reset()
        self.child.reset()


class InverterNode(DecoratorNode):
    """反转器 - 反转子节点结果"""

    def tick(self, context: dict[str, Any]) -> BehaviorStatus:
        status = self.child.tick(context)
        if status == BehaviorStatus.SUCCESS:
            self.status = BehaviorStatus.FAILURE
        elif status == BehaviorStatus.FAILURE:
            self.status = BehaviorStatus.SUCCESS
        else:
            self.status = BehaviorStatus.RUNNING
        return self.status


class RepeatNode(DecoratorNode):
    """重复器 - 重复执行子节点N次"""

    def __init__(self, name: str, child: BehaviorNode, count: int = 3):
        super().__init__(name, child)
        self.count = count
        self._current = 0

    def tick(self, context: dict[str, Any]) -> BehaviorStatus:
        while self._current < self.count:
            status = self.child.tick(context)
            if status == BehaviorStatus.RUNNING:
                self.status = BehaviorStatus.RUNNING
                return BehaviorStatus.RUNNING
            elif status == BehaviorStatus.FAILURE:
                self._current = 0
                self.status = BehaviorStatus.FAILURE
                return BehaviorStatus.FAILURE
            self._current += 1

        self._current = 0
        self.status = BehaviorStatus.SUCCESS
        return BehaviorStatus.SUCCESS

    def reset(self):
        super().reset()
        self._current = 0


class CooldownNode(DecoratorNode):
    """冷却器 - 子节点执行后进入冷却期"""

    def __init__(self, name: str, child: BehaviorNode, cooldown: float = 1.0):
        super().__init__(name, child)
        self.cooldown = cooldown
        self._last_run: float = 0.0

    def tick(self, context: dict[str, Any]) -> BehaviorStatus:
        now = time.time()
        if now - self._last_run < self.cooldown:
            self.status = BehaviorStatus.FAILURE
            return BehaviorStatus.FAILURE

        status = self.child.tick(context)
        if status == BehaviorStatus.SUCCESS:
            self._last_run = now
        self.status = status
        return status


class BehaviorTree:
    """行为树管理器"""

    def __init__(self, root: BehaviorNode, name: str = 'default'):
        self.root = root
        self.name = name
        self._tick_count = 0
        self._last_status = BehaviorStatus.FAILURE

    def tick(self, context: dict[str, Any]) -> BehaviorStatus:
        """执行一次行为树"""
        self._tick_count += 1
        self._last_status = self.root.tick(context)
        return self._last_status

    def reset(self):
        self.root.reset()
        self._tick_count = 0

    @property
    def stats(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'ticks': self._tick_count,
            'last_status': self._last_status.value,
        }

    # ---- 便捷构建方法 ----

    @staticmethod
    def selector(name: str, *children: BehaviorNode) -> SelectorNode:
        return SelectorNode(name, list(children))

    @staticmethod
    def sequence(name: str, *children: BehaviorNode) -> SequenceNode:
        return SequenceNode(name, list(children))

    @staticmethod
    def condition(name: str, fn: Callable[[dict], bool]) -> ConditionNode:
        return ConditionNode(name, fn)

    @staticmethod
    def action(name: str, fn: Callable[[dict], BehaviorStatus]) -> ActionNode:
        return ActionNode(name, fn)
