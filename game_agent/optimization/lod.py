# -*- coding: utf-8 -*-
"""
LOD(Level of Detail)管理器 - 根据性能预算动态调整Agent决策层级

决策层级:
- 反应层(Reactive): 高优先级, 处理紧急威胁, 无缓存
- 战术层(Tactical): 中优先级, 战术决策, 使用缓存
- 战略层(Strategic): 低优先级, 长期规划, 仅在资源充足时执行
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class DecisionLevel(IntEnum):
    REACTIVE = 0  # 反应层 - 始终执行
    TACTICAL = 1  # 战术层 - 中等LOD
    STRATEGIC = 2  # 战略层 - 高LOD


@dataclass
class AgentLOD:
    """Agent的LOD配置"""

    agent_id: str
    importance: float = 0.5  # [0, 1] Agent重要性
    distance_to_player: float = 0.0
    current_level: DecisionLevel = DecisionLevel.TACTICAL
    update_interval: float = 0.5  # 秒


class LODManager:
    """LOD管理器

    根据帧预算(performance_budget)和Agent重要性,
    动态调整每个Agent的决策层级和更新频率。
    """

    def __init__(
        self,
        performance_budget_ms: float = 16.67,  # 60fps
        reactive_budget_ratio: float = 0.5,
        tactical_budget_ratio: float = 0.3,
        strategic_budget_ratio: float = 0.2,
    ):
        self.performance_budget_ms = performance_budget_ms
        self.reactive_budget_ratio = reactive_budget_ratio
        self.tactical_budget_ratio = tactical_budget_ratio
        self.strategic_budget_ratio = strategic_budget_ratio

        self._agents: dict[str, AgentLOD] = {}
        self._frame_times: list[float] = []
        self._max_frame_samples = 60

    def register_agent(
        self,
        agent_id: str,
        importance: float = 0.5,
    ) -> AgentLOD:
        """注册Agent"""
        lod = AgentLOD(agent_id=agent_id, importance=importance)
        self._agents[agent_id] = lod
        return lod

    def unregister_agent(self, agent_id: str):
        self._agents.pop(agent_id, None)

    def update_agent_distance(self, agent_id: str, distance: float):
        """更新Agent到玩家的距离"""
        if agent_id in self._agents:
            self._agents[agent_id].distance_to_player = distance

    def record_frame_time(self, frame_time_ms: float):
        """记录帧时间"""
        self._frame_times.append(frame_time_ms)
        if len(self._frame_times) > self._max_frame_samples:
            self._frame_times.pop(0)

    def compute_lod(self) -> dict[str, AgentLOD]:
        """计算所有Agent的LOD级别

        基于:
        1. 当前帧时间是否在预算内
        2. Agent重要性
        3. Agent到玩家距离
        """
        avg_frame_time = self._avg_frame_time()
        budget_pressure = avg_frame_time / self.performance_budget_ms  # >1 表示超预算

        for _agent_id, lod in self._agents.items():
            lod.current_level = self._compute_agent_level(lod, budget_pressure)
            lod.update_interval = self._compute_update_interval(lod)

        return dict(self._agents)

    def get_agents_for_level(self, level: DecisionLevel) -> list[AgentLOD]:
        """获取指定LOD级别的Agent列表"""
        return [a for a in self._agents.values() if a.current_level >= level]

    def should_update(self, agent_id: str) -> bool:
        """检查Agent是否需要在本帧更新"""
        lod = self._agents.get(agent_id)
        if not lod:
            return False
        # 反应层始终更新
        if lod.current_level == DecisionLevel.REACTIVE:
            return True
        # 其他层按间隔
        return True  # 简化: 实际应基于时间戳判断

    def get_decision_level(self, agent_id: str) -> DecisionLevel:
        lod = self._agents.get(agent_id)
        return lod.current_level if lod else DecisionLevel.REACTIVE

    # ---- 内部逻辑 ----

    def _compute_agent_level(
        self,
        lod: AgentLOD,
        budget_pressure: float,
    ) -> DecisionLevel:
        """计算单个Agent的LOD级别"""
        # 高重要性Agent始终使用高LOD
        if lod.importance >= 0.9:
            return DecisionLevel.STRATEGIC

        # 性能紧张时降级
        if budget_pressure > 1.2:
            # 严重超预算: 只保留反应层
            if lod.importance < 0.5:
                return DecisionLevel.REACTIVE
            return DecisionLevel.TACTICAL

        if budget_pressure > 0.9:
            # 接近预算: 远处Agent降级
            if lod.distance_to_player > 50:
                return DecisionLevel.REACTIVE
            if lod.distance_to_player > 20:
                return DecisionLevel.TACTICAL
            return DecisionLevel.STRATEGIC

        # 预算充足: 根据距离和重要性
        if lod.distance_to_player < 15 or lod.importance > 0.7:
            return DecisionLevel.STRATEGIC
        if lod.distance_to_player < 40:
            return DecisionLevel.TACTICAL
        return DecisionLevel.REACTIVE

    def _compute_update_interval(self, lod: AgentLOD) -> float:
        """计算Agent更新频率"""
        base_intervals = {
            DecisionLevel.REACTIVE: 0.1,
            DecisionLevel.TACTICAL: 0.5,
            DecisionLevel.STRATEGIC: 1.0,
        }
        interval = base_intervals.get(lod.current_level, 0.5)

        # 距离越远, 更新越慢
        distance_factor = 1 + max(0, lod.distance_to_player - 20) * 0.02
        return interval * distance_factor

    def _avg_frame_time(self) -> float:
        if not self._frame_times:
            return 0.0
        return sum(self._frame_times) / len(self._frame_times)

    @property
    def stats(self) -> dict[str, Any]:
        level_counts = {level.name: 0 for level in DecisionLevel}
        for lod in self._agents.values():
            level_counts[lod.current_level.name] += 1
        return {
            'total_agents': len(self._agents),
            'avg_frame_time_ms': round(self._avg_frame_time(), 2),
            'budget_ms': self.performance_budget_ms,
            'level_distribution': level_counts,
        }
