# -*- coding: utf-8 -*-
"""
GameAgent 主类 - 游戏智能Agent的顶层控制器

整合感知→记忆→决策→执行的完整循环, 支持:
- 同步/异步执行模式
- 可插拔的决策策略
- 配置驱动
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from game_agent.core.action import ActionExecutor, ActionResult
from game_agent.core.decision import Action, DecisionModule
from game_agent.core.memory import AgentMemory, MemoryType
from game_agent.core.perception import PerceptionData, PerceptionModule

if TYPE_CHECKING:
    from game_agent.world.game_world import GameWorld


class GameAgent:
    """游戏智能Agent

    核心循环: perceive() -> decide() -> execute()

    Usage:
        agent = GameAgent("npc_01", world, role="guard")
        perception = agent.perceive()
        actions = agent.decide(perception)
        results = agent.execute(actions)
    """

    def __init__(
        self,
        agent_id: str,
        game_world: GameWorld,
        role: str = 'npc',
        position: tuple[float, float, float] = (0, 0, 0),
        config_path: str | None = None,
        **kwargs,
    ):
        self.agent_id = agent_id
        self.game_world = game_world
        self.role = role
        self.position = position
        self.state = 'idle'
        self.health = 1.0
        self.properties: dict[str, Any] = kwargs

        # 加载配置
        self._config = self._load_config(config_path)

        # 初始化核心模块
        mem_cfg = self._config.get('memory', {})
        self.memory = AgentMemory(
            short_term_capacity=mem_cfg.get('short_term_capacity', 20),
            long_term_capacity=mem_cfg.get('long_term_capacity', 1000),
            episodic_capacity=mem_cfg.get('episodic_capacity', 500),
            relevance_threshold=mem_cfg.get('relevance_threshold', 0.3),
        )

        per_cfg = self._config.get('perception', {})
        self.perception = PerceptionModule(
            perception_radius=per_cfg.get('perception_radius', 50.0),
            update_interval=per_cfg.get('update_interval', 0.1),
            event_buffer_size=per_cfg.get('event_buffer_size', 100),
        )

        dec_cfg = self._config.get('decision', {})
        self.decision_maker = DecisionModule(
            strategy=dec_cfg.get('strategy', 'hybrid'),
            decision_interval=dec_cfg.get('decision_interval', 0.5),
            max_actions_per_tick=dec_cfg.get('max_actions_per_tick', 3),
        )

        self.action_executor = ActionExecutor()

        # 在游戏世界中注册
        self.game_world.register_entity(
            entity_id=self.agent_id,
            entity_type=self.role,
            position=self.position,
            health=self.health,
            state=self.state,
        )

        # 统计
        self._tick_count = 0
        self._total_actions = 0

    # ---- 核心循环 ----

    def perceive(self) -> PerceptionData:
        """感知环境"""
        self._sync_state()
        perception_data = self.perception.perceive(
            agent_id=self.agent_id,
            agent_position=self.position,
            game_world=self.game_world,
        )
        # 将感知存入短期记忆
        self.memory.store(
            content={
                'type': 'perception',
                'threats': len(perception_data.threats),
                'players': len(perception_data.visible_players),
                'entities': len(perception_data.nearby_entities),
                'events': len(perception_data.events),
            },
            memory_type=MemoryType.SHORT_TERM,
            importance=0.3 + (0.5 if perception_data.has_threats else 0.0),
            tags=['perception'],
        )
        return perception_data

    def decide(self, perception: PerceptionData) -> list[Action]:
        """做出决策"""
        actions = self.decision_maker.decide(
            perception=perception,
            memory=self.memory,
            current_state=self.state,
            agent_properties={'health': self.health,
                              'role': self.role, **self.properties},
        )
        return actions

    def execute(self, actions: list[Action]) -> list[ActionResult]:
        """执行行动列表"""
        results = []
        for action in actions:
            result = self.action_executor.execute(
                action, self.agent_id, self.game_world)
            results.append(result)

            # 存储交互记忆
            self.memory.store_interaction(
                action=action.action_type.value,
                context={'state': self.state, 'target': action.target},
                result={'success': result.success, 'outcome': result.outcome},
                importance=0.5 if result.success else 0.7,
            )

            self._total_actions += 1

        self._sync_state()
        self._tick_count += 1
        return results

    def tick(self) -> list[ActionResult]:
        """执行一次完整的 感知→决策→执行 循环"""
        perception = self.perceive()
        actions = self.decide(perception)
        return self.execute(actions)

    # ---- 辅助方法 ----

    def _sync_state(self):
        """与游戏世界同步状态"""
        entity = self.game_world.get_entity(self.agent_id)
        if entity:
            self.position = entity.get('position', self.position)
            self.health = entity.get('health', self.health)
            self.state = entity.get('state', self.state)

    def _load_config(self, config_path: str | None) -> dict:
        """加载配置文件"""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}

        # 查找默认配置
        default_paths = [
            Path('configs/default.yaml'),
            Path(__file__).parent.parent / 'configs' / 'default.yaml',
        ]
        for p in default_paths:
            if p.exists():
                with open(p) as f:
                    return yaml.safe_load(f) or {}
        return {}

    @property
    def stats(self) -> dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'role': self.role,
            'state': self.state,
            'health': self.health,
            'position': self.position,
            'ticks': self._tick_count,
            'total_actions': self._total_actions,
            'memory': self.memory.stats,
        }

    def __repr__(self):
        return f'GameAgent(id={self.agent_id}, role={self.role}, state={self.state})'
