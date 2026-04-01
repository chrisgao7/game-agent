# -*- coding: utf-8 -*-
"""对话系统测试"""

from game_agent.npc.dialogue import NPCDialogueSystem, NPCProfile


class TestNPCDialogue:
    def setup_method(self):
        self.profile = NPCProfile(
            name='TestNPC',
            role='铁匠',
            background='一个普通的铁匠',
            personality_traits=['友善'],
        )
        self.dialogue = NPCDialogueSystem(npc_profile=self.profile)

    def test_greeting_response(self):
        """打招呼应返回问候"""
        response = self.dialogue.generate_response('你好')
        assert len(response) > 0

    def test_farewell_response(self):
        response = self.dialogue.generate_response('再见')
        assert len(response) > 0

    def test_unknown_response(self):
        response = self.dialogue.generate_response('量子力学的最新进展是什么？')
        assert len(response) > 0

    def test_history_tracking(self):
        self.dialogue.generate_response('你好')
        self.dialogue.generate_response('你能帮我吗？')
        history = self.dialogue.get_history()
        # 每轮产生2条: player + npc
        assert len(history) == 4

    def test_relationship_positive(self):
        """正面输入应提高关系值"""
        initial = self.profile.relationship_with_player
        self.dialogue.generate_response('谢谢你，太感谢了！')
        assert self.profile.relationship_with_player > initial

    def test_relationship_negative(self):
        """负面输入应降低关系值"""
        initial = self.profile.relationship_with_player
        self.dialogue.generate_response('滚开，讨厌的废物！')
        assert self.profile.relationship_with_player < initial

    def test_emotion_update(self):
        """多次友好交流后NPC情感应变化"""
        for _ in range(20):
            self.dialogue.generate_response('你真棒，谢谢你朋友！')
        assert self.profile.current_emotion in ('happy', 'neutral')

    def test_reset(self):
        self.dialogue.generate_response('你好')
        self.dialogue.reset()
        assert len(self.dialogue.get_history()) == 0
