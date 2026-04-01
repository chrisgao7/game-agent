"""
感知模块 - 获取游戏环境、玩家行为和游戏状态信息

支持:
- 环境感知: 周围实体、地形、物品
- 玩家行为感知: 动作、对话、移动方向
- 事件监听: 游戏事件队列处理
- 感知过滤: 按距离/重要性筛选
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_agent.world.game_world import GameWorld


class EventType(str, Enum):
    PLAYER_ACTION = "player_action"
    PLAYER_SPEAK = "player_speak"
    PLAYER_MOVE = "player_move"
    ENTITY_SPAWN = "entity_spawn"
    ENTITY_DEATH = "entity_death"
    COMBAT_START = "combat_start"
    COMBAT_END = "combat_end"
    ITEM_PICKUP = "item_pickup"
    ENVIRONMENT_CHANGE = "environment_change"
    QUEST_UPDATE = "quest_update"
    CUSTOM = "custom"


@dataclass
class GameEvent:
    """游戏事件"""
    event_type: EventType
    source: str              # 事件来源ID
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 0        # 优先级, 越高越重要


@dataclass
class EntityInfo:
    """实体信息"""
    entity_id: str
    entity_type: str         # player / npc / enemy / item / object
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    health: float = 1.0
    state: str = "idle"
    properties: dict[str, Any] = field(default_factory=dict)
    distance: float = 0.0    # 与当前Agent的距离


@dataclass
class PerceptionData:
    """感知结果数据"""
    nearby_entities: list[EntityInfo] = field(default_factory=list)
    visible_players: list[EntityInfo] = field(default_factory=list)
    threats: list[EntityInfo] = field(default_factory=list)
    events: list[GameEvent] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def has_threats(self) -> bool:
        return len(self.threats) > 0

    @property
    def has_players_nearby(self) -> bool:
        return len(self.visible_players) > 0


class PerceptionModule:
    """感知模块

    负责从游戏世界中采集并处理环境信息, 生成结构化的感知数据供决策模块使用。
    """

    def __init__(
        self,
        perception_radius: float = 50.0,
        update_interval: float = 0.1,
        event_buffer_size: int = 100,
    ):
        self.perception_radius = perception_radius
        self.update_interval = update_interval
        self._event_buffer: deque[GameEvent] = deque(maxlen=event_buffer_size)
        self._last_update: float = 0.0
        self._event_listeners: dict[EventType, list] = {}

    def perceive(
        self,
        agent_id: str,
        agent_position: tuple[float, float, float],
        game_world: GameWorld,
    ) -> PerceptionData:
        """执行一次完整的环境感知

        Args:
            agent_id: 当前Agent的ID
            agent_position: 当前Agent的位置
            game_world: 游戏世界实例
        """
        now = time.time()
        self._last_update = now

        # 1. 获取附近实体
        nearby = self._scan_entities(agent_id, agent_position, game_world)

        # 2. 筛选可见玩家
        players = [e for e in nearby if e.entity_type == "player"]

        # 3. 识别威胁
        threats = self._identify_threats(nearby, agent_id, game_world)

        # 4. 收集事件
        events = self._collect_events(agent_id, game_world)

        # 5. 获取环境信息
        environment = self._sense_environment(agent_position, game_world)

        return PerceptionData(
            nearby_entities=nearby,
            visible_players=players,
            threats=threats,
            events=events,
            environment=environment,
            timestamp=now,
        )

    def push_event(self, event: GameEvent):
        """外部推送事件到感知缓冲区"""
        self._event_buffer.append(event)
        self._dispatch_event(event)

    def register_listener(self, event_type: EventType, callback):
        """注册事件监听器"""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)

    def unregister_listener(self, event_type: EventType, callback):
        """取消事件监听器"""
        if event_type in self._event_listeners:
            self._event_listeners[event_type] = [
                cb for cb in self._event_listeners[event_type] if cb != callback
            ]

    # ---- 内部方法 ----

    def _scan_entities(
        self,
        agent_id: str,
        position: tuple[float, float, float],
        game_world: GameWorld,
    ) -> list[EntityInfo]:
        """扫描感知范围内的实体"""
        entities = game_world.get_entities_in_radius(position, self.perception_radius)
        result = []
        for entity_data in entities:
            if entity_data.get("id") == agent_id:
                continue
            entity_pos = entity_data.get("position", (0, 0, 0))
            dist = self._distance(position, entity_pos)
            info = EntityInfo(
                entity_id=entity_data.get("id", "unknown"),
                entity_type=entity_data.get("type", "unknown"),
                position=entity_pos,
                health=entity_data.get("health", 1.0),
                state=entity_data.get("state", "idle"),
                properties=entity_data.get("properties", {}),
                distance=dist,
            )
            result.append(info)
        # 按距离排序
        result.sort(key=lambda e: e.distance)
        return result

    def _identify_threats(
        self,
        entities: list[EntityInfo],
        agent_id: str,
        game_world: GameWorld,
    ) -> list[EntityInfo]:
        """识别威胁实体"""
        threats = []
        for entity in entities:
            is_threat = (
                entity.entity_type == "enemy"
                or entity.state in ("attacking", "hostile", "aggressive")
                or game_world.is_hostile(entity.entity_id, agent_id)
            )
            if is_threat:
                threats.append(entity)
        return threats

    def _collect_events(self, agent_id: str, game_world: GameWorld) -> list[GameEvent]:
        """收集与当前Agent相关的事件"""
        # 从游戏世界获取事件
        world_events = game_world.get_events_for(agent_id)
        for evt in world_events:
            self._event_buffer.append(evt)

        # 取出缓冲区中的所有事件
        events = list(self._event_buffer)
        self._event_buffer.clear()

        # 按优先级排序
        events.sort(key=lambda e: e.priority, reverse=True)
        return events

    def _sense_environment(
        self,
        position: tuple[float, float, float],
        game_world: GameWorld,
    ) -> dict[str, Any]:
        """感知环境信息"""
        return {
            "time_of_day": game_world.get_time_of_day(),
            "weather": game_world.get_weather(),
            "location": game_world.get_location_name(position),
            "terrain": game_world.get_terrain(position),
            "light_level": game_world.get_light_level(position),
        }

    def _dispatch_event(self, event: GameEvent):
        """分发事件给监听器"""
        listeners = self._event_listeners.get(event.event_type, [])
        for callback in listeners:
            try:
                callback(event)
            except Exception:
                pass

    @staticmethod
    def _distance(
        a: tuple[float, float, float],
        b: tuple[float, float, float],
    ) -> float:
        return ((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) ** 0.5
