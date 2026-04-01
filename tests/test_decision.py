# -*- coding: utf-8 -*-
"""决策模块测试"""

from game_agent.core.decision import ActionType, DecisionModule
from game_agent.core.memory import AgentMemory
from game_agent.core.perception import EntityInfo, PerceptionData


class TestDecisionModule:
    def setup_method(self):
        self.decision = DecisionModule()
        self.memory = AgentMemory()

    def test_idle_decision(self):
        """空闲状态应生成巡逻或idle行动"""
        perception = PerceptionData()
        actions = self.decision.decide(
            perception, self.memory, current_state='idle')
        assert len(actions) > 0
        assert actions[0].action_type in (ActionType.PATROL, ActionType.IDLE)

    def test_threat_response(self):
        """发现威胁应生成攻击行动"""
        threat = EntityInfo(entity_id='enemy_01',
                            entity_type='enemy', state='hostile', distance=10)
        perception = PerceptionData(threats=[threat])
        actions = self.decision.decide(
            perception, self.memory, current_state='alert')
        assert any(a.action_type == ActionType.ATTACK for a in actions)

    def test_low_health_flee(self):
        """低生命值应生成逃跑行动"""
        threat = EntityInfo(entity_id='enemy_01',
                            entity_type='enemy', state='hostile', distance=5)
        perception = PerceptionData(threats=[threat])
        actions = self.decision.decide(
            perception,
            self.memory,
            current_state='combat',
            agent_properties={'health': 0.1},
        )
        assert actions[0].action_type == ActionType.FLEE

    def test_player_interaction(self):
        """附近有玩家应触发交互"""
        player = EntityInfo(entity_id='player_01',
                            entity_type='player', distance=5)
        perception = PerceptionData(visible_players=[player])
        actions = self.decision.decide(
            perception, self.memory, current_state='patrol')
        assert any(a.action_type == ActionType.INTERACT for a in actions)

    def test_priority_ordering(self):
        """行动应按优先级排序"""
        threat = EntityInfo(entity_id='enemy_01',
                            entity_type='enemy', state='hostile', distance=10)
        perception = PerceptionData(threats=[threat])
        actions = self.decision.decide(
            perception,
            self.memory,
            current_state='idle',
            agent_properties={'health': 0.15},
        )
        # FLEE应排在ATTACK前面(因为CRITICAL > HIGH)
        assert actions[0].action_type == ActionType.FLEE
