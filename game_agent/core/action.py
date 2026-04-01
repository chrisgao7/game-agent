"""
行动执行器 - 执行决策模块产生的行动, 与游戏世界交互并返回结果
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from game_agent.core.decision import Action, ActionType

if TYPE_CHECKING:
    from game_agent.world.game_world import GameWorld


@dataclass
class ActionResult:
    """行动执行结果"""
    action: Action
    success: bool
    outcome: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0   # 执行耗时(秒)


class ActionExecutor:
    """行动执行器

    将决策模块产生的Action翻译为游戏世界API调用,
    执行后返回ActionResult供记忆模块存储。
    """

    def __init__(self):
        self._handlers: dict[ActionType, Any] = {}
        self._setup_default_handlers()
        self._execution_history: list[ActionResult] = []
        self._max_history = 100

    def execute(
        self,
        action: Action,
        agent_id: str,
        game_world: GameWorld,
    ) -> ActionResult:
        """执行一个行动

        Args:
            action: 要执行的行动
            agent_id: 当前Agent ID
            game_world: 游戏世界实例
        """
        start = time.time()

        handler = self._handlers.get(action.action_type)
        if handler is None:
            result = ActionResult(
                action=action,
                success=False,
                message=f"No handler for action type: {action.action_type}",
            )
        else:
            try:
                outcome = handler(action, agent_id, game_world)
                result = ActionResult(
                    action=action,
                    success=True,
                    outcome=outcome,
                    message="ok",
                )
            except Exception as e:
                result = ActionResult(
                    action=action,
                    success=False,
                    message=f"Execution error: {e}",
                )

        result.duration = time.time() - start
        self._record(result)
        return result

    def register_handler(self, action_type: ActionType, handler):
        """注册自定义行动处理器

        handler签名: (action: Action, agent_id: str, game_world: GameWorld) -> dict
        """
        self._handlers[action_type] = handler

    def get_history(self, n: int = 10) -> list[ActionResult]:
        """获取最近n条执行历史"""
        return self._execution_history[-n:]

    # ---- 默认处理器 ----

    def _setup_default_handlers(self):
        self._handlers = {
            ActionType.MOVE: self._handle_move,
            ActionType.ATTACK: self._handle_attack,
            ActionType.DEFEND: self._handle_defend,
            ActionType.PATROL: self._handle_patrol,
            ActionType.INTERACT: self._handle_interact,
            ActionType.SPEAK: self._handle_speak,
            ActionType.FLEE: self._handle_flee,
            ActionType.IDLE: self._handle_idle,
            ActionType.USE_ITEM: self._handle_use_item,
            ActionType.INVESTIGATE: self._handle_investigate,
            ActionType.FOLLOW: self._handle_follow,
        }

    def _handle_move(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        target_pos = action.parameters.get("position", (0, 0, 0))
        world.move_entity(agent_id, target_pos)
        return {"new_position": target_pos}

    def _handle_attack(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        damage = action.parameters.get("damage", 10)
        result = world.apply_damage(agent_id, action.target, damage)
        return {"target": action.target, "damage": damage, "result": result}

    def _handle_defend(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        world.set_entity_state(agent_id, "defending")
        return {"state": "defending"}

    def _handle_patrol(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        waypoints = action.parameters.get("waypoints", [])
        next_point = world.get_next_patrol_point(agent_id, waypoints)
        if next_point:
            world.move_entity(agent_id, next_point)
        return {"moving_to": next_point}

    def _handle_interact(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        interaction_type = action.parameters.get("interaction_type", "greet")
        result = world.interact(agent_id, action.target, interaction_type)
        return {"interaction": interaction_type, "target": action.target, "result": result}

    def _handle_speak(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        message = action.parameters.get("message", "")
        world.send_message(agent_id, action.target, message)
        return {"message": message, "target": action.target}

    def _handle_flee(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        safe_pos = world.find_safe_position(agent_id)
        world.move_entity(agent_id, safe_pos)
        world.set_entity_state(agent_id, "fleeing")
        return {"fleeing_to": safe_pos}

    def _handle_idle(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        world.set_entity_state(agent_id, "idle")
        return {"state": "idle"}

    def _handle_use_item(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        item_id = action.parameters.get("item_id", "")
        result = world.use_item(agent_id, item_id)
        return {"item": item_id, "result": result}

    def _handle_investigate(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        target_pos = action.parameters.get("position", (0, 0, 0))
        world.move_entity(agent_id, target_pos)
        world.set_entity_state(agent_id, "investigating")
        return {"investigating": target_pos}

    def _handle_follow(self, action: Action, agent_id: str, world: GameWorld) -> dict:
        target_pos = world.get_entity_position(action.target)
        if target_pos:
            world.move_entity(agent_id, target_pos)
        return {"following": action.target}

    def _record(self, result: ActionResult):
        self._execution_history.append(result)
        if len(self._execution_history) > self._max_history:
            self._execution_history.pop(0)
