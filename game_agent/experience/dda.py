# -*- coding: utf-8 -*-
"""
动态难度调整(DDA) - 实时监控玩家表现, 自适应调整游戏参数

采集指标: 成功率/完成时间/死亡率/资源消耗
调整目标: NPC参数/敌人参数/资源参数
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlayerAction:
    """玩家行为记录"""

    action_type: str  # combat / exploration / puzzle / quest
    success: bool
    duration: float = 0.0  # 秒
    damage_taken: float = 0.0
    resources_used: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class DifficultyParams:
    """难度参数集"""

    # NPC参数
    npc_reaction_time: float = 1.0  # 秒, 越低越难
    npc_accuracy: float = 0.5  # [0,1], 越高越难
    npc_aggression: float = 0.5  # [0,1], 越高越难

    # 敌人参数
    enemy_spawn_rate: float = 1.0  # 倍率
    enemy_health_multiplier: float = 1.0
    enemy_damage_multiplier: float = 1.0

    # 资源参数
    health_pack_rate: float = 1.0  # 倍率
    ammo_availability: float = 1.0

    # 综合难度
    overall_difficulty: float = 0.5  # [0, 1]


class DynamicDifficultyAdjustment:
    """动态难度调整系统

    持续监控玩家表现, 通过评分机制计算综合表现,
    当表现偏离目标时自动调整游戏难度参数。
    """

    def __init__(
        self,
        target_success_rate: float = 0.6,
        adjustment_speed: float = 0.1,
        min_difficulty: float = 0.2,
        max_difficulty: float = 1.0,
        evaluation_window: int = 10,
    ):
        self.target_success_rate = target_success_rate
        self.adjustment_speed = adjustment_speed
        self.min_difficulty = min_difficulty
        self.max_difficulty = max_difficulty
        self.evaluation_window = evaluation_window

        self.params = DifficultyParams()
        self._action_history: deque[PlayerAction] = deque(
            maxlen=evaluation_window * 5)
        self._adjustment_history: list[dict[str, Any]] = []

    def record_player_action(self, action: PlayerAction):
        """记录玩家行为"""
        self._action_history.append(action)

    def record(
        self,
        action_type: str,
        success: bool,
        duration: float = 0.0,
        damage_taken: float = 0.0,
        resources_used: float = 0.0,
    ):
        """便捷记录接口"""
        self.record_player_action(
            PlayerAction(
                action_type=action_type,
                success=success,
                duration=duration,
                damage_taken=damage_taken,
                resources_used=resources_used,
            )
        )

    def calculate_performance_score(self) -> float:
        """计算玩家综合表现分数 [0, 1]

        权重:
        - 成功率: 0.4
        - 完成效率: 0.25
        - 存活能力: 0.2
        - 资源效率: 0.15
        """
        recent = list(self._action_history)[-self.evaluation_window:]
        if not recent:
            return 0.5

        # 成功率
        successes = sum(1 for a in recent if a.success)
        success_rate = successes / len(recent)

        # 完成效率 (基于预期时间, 归一化)
        avg_duration = sum(a.duration for a in recent) / \
            len(recent) if recent else 0
        expected_duration = 30.0  # 基准时间
        efficiency = (
            max(0, min(1, 1 - (avg_duration - expected_duration) / expected_duration))
            if expected_duration > 0
            else 0.5
        )

        # 存活能力 (低伤害 = 高分)
        avg_damage = sum(a.damage_taken for a in recent) / \
            len(recent) if recent else 0
        survival = max(0, min(1, 1 - avg_damage))

        # 资源效率 (低消耗 = 高分)
        avg_resources = sum(a.resources_used for a in recent) / \
            len(recent) if recent else 0
        resource_eff = max(0, min(1, 1 - avg_resources))

        score = 0.40 * success_rate + 0.25 * efficiency + \
            0.20 * survival + 0.15 * resource_eff
        return score

    def adjust_difficulty(self) -> DifficultyParams:
        """根据表现调整难度

        Returns:
            调整后的难度参数
        """
        performance = self.calculate_performance_score()

        # 计算差值: 表现太好 → 提高难度, 表现不好 → 降低难度
        delta = (performance - self.target_success_rate) * \
            self.adjustment_speed

        # 更新综合难度
        new_difficulty = self.params.overall_difficulty + delta
        new_difficulty = max(self.min_difficulty, min(
            self.max_difficulty, new_difficulty))
        self.params.overall_difficulty = new_difficulty

        # 映射到具体参数
        self._apply_difficulty(new_difficulty)

        # 记录调整历史
        self._adjustment_history.append(
            {
                'timestamp': time.time(),
                'performance': performance,
                'delta': delta,
                'difficulty': new_difficulty,
            }
        )

        return self.params

    def _apply_difficulty(self, difficulty: float):
        """将综合难度映射到具体参数"""
        d = difficulty

        # NPC参数: 难度越高, 反应越快/越准/越凶
        self.params.npc_reaction_time = 1.5 - d * 1.0  # [0.5, 1.5]
        self.params.npc_accuracy = 0.3 + d * 0.5  # [0.3, 0.8]
        self.params.npc_aggression = 0.2 + d * 0.6  # [0.2, 0.8]

        # 敌人参数
        self.params.enemy_spawn_rate = 0.5 + d * 1.0  # [0.5, 1.5]
        self.params.enemy_health_multiplier = 0.6 + d * 0.8  # [0.6, 1.4]
        self.params.enemy_damage_multiplier = 0.6 + d * 0.8

        # 资源参数: 难度越高, 资源越少
        self.params.health_pack_rate = 1.5 - d * 1.0  # [0.5, 1.5]
        self.params.ammo_availability = 1.3 - d * 0.6  # [0.7, 1.3]

    def get_adjustment_history(self, n: int = 10) -> list[dict[str, Any]]:
        return self._adjustment_history[-n:]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            'difficulty': self.params.overall_difficulty,
            'target_success_rate': self.target_success_rate,
            'recent_performance': self.calculate_performance_score(),
            'total_actions_recorded': len(self._action_history),
            'total_adjustments': len(self._adjustment_history),
        }
