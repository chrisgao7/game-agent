"""
游戏世界接口 - 定义Agent与游戏世界交互的标准接口

GameWorld 是一个可被具体游戏引擎实现的抽象层,
提供实体管理、物理交互、事件系统等基础能力。
"""

from __future__ import annotations

import time
import random
from typing import Any, Optional

from game_agent.core.perception import GameEvent, EventType


class GameWorld:
    """游戏世界

    提供Agent与游戏环境交互的标准接口。
    默认实现为简单的内存模拟, 实际使用时应子类化并对接游戏引擎。
    """

    def __init__(self):
        self._entities: dict[str, dict[str, Any]] = {}
        self._event_queue: dict[str, list[GameEvent]] = {}  # agent_id -> events
        self._time_of_day: str = "day"
        self._weather: str = "clear"
        self._hostility: dict[tuple[str, str], bool] = {}
        self._patrol_indices: dict[str, int] = {}

    # ---- 实体管理 ----

    def register_entity(
        self,
        entity_id: str,
        entity_type: str,
        position: tuple[float, float, float] = (0, 0, 0),
        health: float = 1.0,
        state: str = "idle",
        properties: dict[str, Any] | None = None,
    ):
        """注册实体到世界"""
        self._entities[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            "position": position,
            "health": health,
            "state": state,
            "properties": properties or {},
        }

    def remove_entity(self, entity_id: str):
        """移除实体"""
        self._entities.pop(entity_id, None)

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        return self._entities.get(entity_id)

    def get_entity_position(self, entity_id: str) -> tuple[float, float, float] | None:
        entity = self._entities.get(entity_id)
        if entity:
            return entity.get("position")
        return None

    def get_entities_in_radius(
        self,
        center: tuple[float, float, float],
        radius: float,
    ) -> list[dict[str, Any]]:
        """获取指定范围内的实体"""
        result = []
        for entity in self._entities.values():
            pos = entity.get("position", (0, 0, 0))
            dist = (
                (center[0] - pos[0]) ** 2
                + (center[1] - pos[1]) ** 2
                + (center[2] - pos[2]) ** 2
            ) ** 0.5
            if dist <= radius:
                result.append(entity)
        return result

    # ---- 实体操作 ----

    def move_entity(self, entity_id: str, position: tuple[float, float, float]):
        if entity_id in self._entities:
            self._entities[entity_id]["position"] = position

    def set_entity_state(self, entity_id: str, state: str):
        if entity_id in self._entities:
            self._entities[entity_id]["state"] = state

    def apply_damage(
        self,
        attacker_id: str,
        target_id: str | None,
        damage: float,
    ) -> dict[str, Any]:
        """施加伤害"""
        if not target_id or target_id not in self._entities:
            return {"hit": False, "reason": "target_not_found"}
        target = self._entities[target_id]
        target["health"] = max(0.0, target["health"] - damage / 100.0)
        dead = target["health"] <= 0
        if dead:
            target["state"] = "dead"
        return {"hit": True, "remaining_health": target["health"], "dead": dead}

    def interact(
        self,
        source_id: str,
        target_id: str | None,
        interaction_type: str,
    ) -> dict[str, Any]:
        """实体间交互"""
        return {"source": source_id, "target": target_id, "type": interaction_type, "success": True}

    def send_message(self, sender_id: str, receiver_id: str | None, message: str):
        """发送消息"""
        if receiver_id:
            event = GameEvent(
                event_type=EventType.PLAYER_SPEAK,
                source=sender_id,
                data={"message": message},
            )
            self._event_queue.setdefault(receiver_id, []).append(event)

    def use_item(self, entity_id: str, item_id: str) -> dict[str, Any]:
        return {"entity": entity_id, "item": item_id, "used": True}

    def find_safe_position(self, entity_id: str) -> tuple[float, float, float]:
        """查找安全位置(简单实现: 远离威胁方向)"""
        entity = self._entities.get(entity_id)
        if entity:
            pos = entity["position"]
            # 向随机方向移动
            offset = (random.uniform(-20, 20), 0, random.uniform(-20, 20))
            return (pos[0] + offset[0], pos[1] + offset[1], pos[2] + offset[2])
        return (0, 0, 0)

    def get_next_patrol_point(
        self,
        agent_id: str,
        waypoints: list[tuple[float, float, float]],
    ) -> tuple[float, float, float] | None:
        """获取下一个巡逻点"""
        if not waypoints:
            return None
        idx = self._patrol_indices.get(agent_id, 0)
        point = waypoints[idx % len(waypoints)]
        self._patrol_indices[agent_id] = idx + 1
        return point

    # ---- 环境信息 ----

    def get_time_of_day(self) -> str:
        return self._time_of_day

    def set_time_of_day(self, tod: str):
        self._time_of_day = tod

    def get_weather(self) -> str:
        return self._weather

    def set_weather(self, weather: str):
        self._weather = weather

    def get_location_name(self, position: tuple[float, float, float]) -> str:
        return "default_zone"

    def get_terrain(self, position: tuple[float, float, float]) -> str:
        return "flat"

    def get_light_level(self, position: tuple[float, float, float]) -> float:
        return 1.0 if self._time_of_day == "day" else 0.3

    # ---- 事件系统 ----

    def get_events_for(self, agent_id: str) -> list[GameEvent]:
        """获取指定Agent的待处理事件"""
        events = self._event_queue.pop(agent_id, [])
        return events

    def push_event(self, agent_id: str, event: GameEvent):
        self._event_queue.setdefault(agent_id, []).append(event)

    # ---- 关系系统 ----

    def is_hostile(self, entity_a: str, entity_b: str) -> bool:
        return self._hostility.get((entity_a, entity_b), False)

    def set_hostility(self, entity_a: str, entity_b: str, hostile: bool = True):
        self._hostility[(entity_a, entity_b)] = hostile
        self._hostility[(entity_b, entity_a)] = hostile
