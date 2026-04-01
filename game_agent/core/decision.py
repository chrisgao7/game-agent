"""
决策模块 - 基于感知和记忆生成行动方案

支持多种决策策略:
- hybrid: 行为树+状态机融合 (默认)
- behavior_tree: 纯行为树
- state_machine: 纯状态机
- llm: LLM推理决策
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from game_agent.core.memory import AgentMemory, MemoryType
from game_agent.core.perception import PerceptionData


class ActionType(str, Enum):
    MOVE = "move"
    ATTACK = "attack"
    DEFEND = "defend"
    PATROL = "patrol"
    INTERACT = "interact"
    SPEAK = "speak"
    FLEE = "flee"
    IDLE = "idle"
    USE_ITEM = "use_item"
    INVESTIGATE = "investigate"
    FOLLOW = "follow"
    CUSTOM = "custom"


class ActionPriority(int, Enum):
    CRITICAL = 100     # 生死攸关
    HIGH = 75          # 紧急任务
    MEDIUM = 50        # 常规任务
    LOW = 25           # 空闲行为
    BACKGROUND = 0     # 背景动作


@dataclass
class Action:
    """行动方案"""
    action_type: ActionType
    target: Optional[str] = None        # 目标ID
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: ActionPriority = ActionPriority.MEDIUM
    confidence: float = 1.0             # 决策置信度 [0, 1]
    source: str = "decision_module"     # 决策来源
    timestamp: float = field(default_factory=time.time)

    def __repr__(self):
        return f"Action({self.action_type.value}, target={self.target}, priority={self.priority.name})"


class DecisionModule:
    """决策模块

    综合感知数据和记忆信息, 生成最优行动方案。
    支持多种决策策略, 默认使用hybrid(行为树+状态机融合)模式。
    """

    def __init__(
        self,
        strategy: str = "hybrid",
        decision_interval: float = 0.5,
        max_actions_per_tick: int = 3,
    ):
        self.strategy = strategy
        self.decision_interval = decision_interval
        self.max_actions_per_tick = max_actions_per_tick
        self._last_decision_time: float = 0.0
        self._decision_rules: list[DecisionRule] = []
        self._setup_default_rules()

    def decide(
        self,
        perception: PerceptionData,
        memory: AgentMemory,
        current_state: str = "idle",
        agent_properties: dict[str, Any] | None = None,
    ) -> list[Action]:
        """做出决策, 返回行动列表(按优先级排序)

        Args:
            perception: 当前感知数据
            memory: 记忆模块
            current_state: 当前状态
            agent_properties: Agent属性(生命值等)
        """
        now = time.time()
        self._last_decision_time = now

        props = agent_properties or {}

        # 检索相关记忆
        query = {
            "has_threats": perception.has_threats,
            "has_players": perception.has_players_nearby,
            "state": current_state,
        }
        relevant_memories = memory.retrieve(query, top_k=5)

        # 生成候选行动
        candidates = self._generate_candidates(perception, relevant_memories, current_state, props)

        # 评估并排序
        evaluated = self._evaluate_candidates(candidates, perception, props)

        # 返回前N个
        return evaluated[: self.max_actions_per_tick]

    def add_rule(self, rule: DecisionRule):
        """添加自定义决策规则"""
        self._decision_rules.append(rule)
        self._decision_rules.sort(key=lambda r: r.priority, reverse=True)

    def _generate_candidates(
        self,
        perception: PerceptionData,
        memories: list,
        current_state: str,
        properties: dict[str, Any],
    ) -> list[Action]:
        """根据规则生成候选行动"""
        candidates = []
        context = DecisionContext(
            perception=perception,
            memories=memories,
            current_state=current_state,
            properties=properties,
        )

        for rule in self._decision_rules:
            if rule.condition(context):
                action = rule.generate_action(context)
                if action:
                    candidates.append(action)

        # 如果没有匹配的规则, 生成默认idle行动
        if not candidates:
            candidates.append(Action(action_type=ActionType.IDLE, priority=ActionPriority.BACKGROUND))

        return candidates

    def _evaluate_candidates(
        self,
        candidates: list[Action],
        perception: PerceptionData,
        properties: dict[str, Any],
    ) -> list[Action]:
        """评估候选行动, 按优先级和置信度综合排序"""
        def score(action: Action) -> float:
            return action.priority.value * action.confidence

        candidates.sort(key=score, reverse=True)
        return candidates

    def _setup_default_rules(self):
        """设置默认决策规则"""
        # 规则1: 生命危急 → 逃跑
        self.add_rule(DecisionRule(
            name="critical_health_flee",
            priority=100,
            condition=lambda ctx: ctx.properties.get("health", 1.0) < 0.2,
            generate_action=lambda ctx: Action(
                action_type=ActionType.FLEE,
                priority=ActionPriority.CRITICAL,
                confidence=0.9,
                source="rule:critical_health",
            ),
        ))

        # 规则2: 发现威胁 → 攻击/防御
        self.add_rule(DecisionRule(
            name="threat_response",
            priority=90,
            condition=lambda ctx: ctx.perception.has_threats,
            generate_action=lambda ctx: Action(
                action_type=ActionType.ATTACK,
                target=ctx.perception.threats[0].entity_id if ctx.perception.threats else None,
                priority=ActionPriority.HIGH,
                confidence=0.8,
                source="rule:threat_response",
            ),
        ))

        # 规则3: 附近有玩家 → 交互
        self.add_rule(DecisionRule(
            name="player_interaction",
            priority=50,
            condition=lambda ctx: (
                ctx.perception.has_players_nearby
                and not ctx.perception.has_threats
            ),
            generate_action=lambda ctx: Action(
                action_type=ActionType.INTERACT,
                target=ctx.perception.visible_players[0].entity_id if ctx.perception.visible_players else None,
                priority=ActionPriority.MEDIUM,
                confidence=0.7,
                source="rule:player_interaction",
            ),
        ))

        # 规则4: 空闲 → 巡逻
        self.add_rule(DecisionRule(
            name="idle_patrol",
            priority=10,
            condition=lambda ctx: ctx.current_state == "idle",
            generate_action=lambda ctx: Action(
                action_type=ActionType.PATROL,
                priority=ActionPriority.LOW,
                confidence=0.6,
                source="rule:idle_patrol",
            ),
        ))


@dataclass
class DecisionContext:
    """决策上下文"""
    perception: PerceptionData
    memories: list
    current_state: str
    properties: dict[str, Any]


@dataclass
class DecisionRule:
    """决策规则"""
    name: str
    priority: int
    condition: Any      # Callable[[DecisionContext], bool]
    generate_action: Any  # Callable[[DecisionContext], Action | None]
