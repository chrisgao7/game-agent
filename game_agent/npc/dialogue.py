# -*- coding: utf-8 -*-
"""
NPC对话系统 - 集成LLM实现智能化NPC对话

特性:
- Prompt Engineering: 动态构建包含角色背景/性格/情感/关系的系统提示
- 上下文管理: 保留最近N轮对话历史 + 游戏环境注入
- 情感分析: 实时分析玩家输入的情感, 更新NPC状态
- 降级策略: LLM调用失败时回退到预设回应
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

from game_agent.utils.llm_client import LLMClient


@dataclass
class DialogueTurn:
    """一轮对话"""

    role: str  # "player" or "npc"
    content: str
    timestamp: float = field(default_factory=time.time)
    emotion: str = 'neutral'


@dataclass
class NPCProfile:
    """NPC角色档案"""

    name: str
    role: str  # 职业/身份
    background: str  # 背景故事
    personality_traits: list[str]  # 性格特征
    speaking_style: str = ''  # 说话风格
    knowledge: list[str] = field(default_factory=list)  # 知识范围
    current_emotion: str = 'neutral'
    relationship_with_player: int = 0  # -100 到 100


class NPCDialogueSystem:
    """NPC智能对话系统

    通过LLM生成上下文相关、角色一致的NPC对话回复。
    支持情感状态追踪和关系系统。
    """

    def __init__(
        self,
        npc_profile: NPCProfile,
        llm_config: dict[str, Any] | None = None,
        llm_client: LLMClient | None = None,
        max_history: int = 10,
    ):
        self.profile = npc_profile
        self.max_history = max_history
        self._history: list[DialogueTurn] = []
        self._llm_config = llm_config or {}

        # LLM 客户端: 优先使用外部传入的client, 否则根据配置创建
        if llm_client is not None:
            self._client = llm_client
        elif self._llm_config.get('api_key') or self._llm_config.get('base_url'):
            self._client = LLMClient(self._llm_config)
        else:
            self._client = None

        # 预设回应(降级用)
        self._fallback_responses = {
            'greeting': [
                f'你好，旅行者。我是{npc_profile.name}。',
                '欢迎来到这里。有什么我能帮助你的吗？',
                '嗯？你找我有事？',
            ],
            'farewell': [
                '再见，祝你旅途顺利。',
                '保重，冒险者。',
                '下次再来找我。',
            ],
            'unknown': [
                '嗯...让我想想...',
                '这个我不太清楚。',
                f'作为{npc_profile.role}，这超出了我的能力范围。',
            ],
            'hostile': [
                '离我远点！',
                '你不受欢迎。',
                '我没什么好跟你说的。',
            ],
            'friendly': [
                '老朋友，见到你真高兴！',
                '我一直在等你来！',
                '有什么需要尽管说。',
            ],
        }

    def generate_response(
        self,
        player_input: str,
        game_context: dict[str, Any] | None = None,
    ) -> str:
        """生成NPC对话回复

        Args:
            player_input: 玩家输入的文本
            game_context: 当前游戏上下文(位置、时间、事件等)

        Returns:
            NPC的回复文本
        """
        # 记录玩家输入
        player_emotion = self._analyze_sentiment(player_input)
        self._history.append(
            DialogueTurn(
                role='player',
                content=player_input,
                emotion=player_emotion,
            )
        )

        # 更新NPC状态
        self._update_state(player_input, player_emotion)

        # 尝试LLM生成
        response = self._llm_generate(player_input, game_context)

        if response is None:
            # 降级到预设回应
            response = self._fallback_response(player_input)

        # 记录NPC回复
        self._history.append(
            DialogueTurn(
                role='npc',
                content=response,
                emotion=self.profile.current_emotion,
            )
        )

        # 保持历史长度
        if len(self._history) > self.max_history * 2:
            self._history = self._history[-self.max_history * 2:]

        return response

    def get_history(self) -> list[DialogueTurn]:
        return list(self._history)

    def reset(self):
        self._history.clear()

    # ---- LLM 集成 ----

    def _llm_generate(
        self,
        player_input: str,
        game_context: dict[str, Any] | None,
    ) -> str | None:
        """调用LLM生成回复"""
        if not self._client:
            return None

        try:
            system_prompt = self._build_system_prompt(game_context)
            messages = [{'role': 'system', 'content': system_prompt}]

            # 注入对话历史
            for turn in self._history[-self.max_history:]:
                role = 'user' if turn.role == 'player' else 'assistant'
                messages.append({'role': role, 'content': turn.content})

            return self._client.chat_completions(messages)

        except Exception:
            return None

    def _build_system_prompt(self, game_context: dict[str, Any] | None) -> str:
        """构建系统提示词"""
        p = self.profile
        ctx = game_context or {}

        prompt = f"""你是一个游戏NPC角色，请严格按照以下设定进行对话回应：

【角色信息】
- 名字: {p.name}
- 身份: {p.role}
- 背景: {p.background}
- 性格特征: {", ".join(p.personality_traits)}
- 说话风格: {p.speaking_style or "正常"}
- 当前情感: {p.current_emotion}
- 与玩家关系: {self._relationship_desc()}

【知识范围】
{chr(10).join("- " + k for k in p.knowledge) if p.knowledge else "- 一般常识"}

【游戏环境】
- 位置: {ctx.get("location", "未知")}
- 时间: {ctx.get("time_of_day", "白天")}
- 天气: {ctx.get("weather", "晴朗")}
- 最近事件: {ctx.get("recent_events", "无")}

【对话规则】
1. 始终保持角色一致性，不要跳出角色设定
2. 回复长度控制在1-3句话
3. 根据当前情感状态调整语气
4. 如果玩家询问超出知识范围的事情，委婉表示不知道
5. 根据与玩家的关系亲密度调整态度
"""
        return prompt

    # ---- 情感与关系 ----

    def _analyze_sentiment(self, text: str) -> str:
        """简单的情感分析"""
        positive_words = {'谢谢', '感谢', '太好了', '棒', '喜欢', '帮助', '朋友', '你好', '嗨'}
        negative_words = {'滚', '讨厌', '笨', '废物', '杀', '死', '攻击', '打', '恨'}

        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)

        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        return 'neutral'

    def _update_state(self, player_input: str, emotion: str):
        """更新NPC状态"""
        # 更新关系值
        if emotion == 'positive':
            self.profile.relationship_with_player = min(
                100, self.profile.relationship_with_player + 3
            )
        elif emotion == 'negative':
            self.profile.relationship_with_player = max(
                -100, self.profile.relationship_with_player - 5
            )

        # 更新NPC情感
        rel = self.profile.relationship_with_player
        if rel > 50:
            self.profile.current_emotion = 'happy'
        elif rel > 0:
            self.profile.current_emotion = 'neutral'
        elif rel > -30:
            self.profile.current_emotion = 'wary'
        else:
            self.profile.current_emotion = 'hostile'

    def _relationship_desc(self) -> str:
        rel = self.profile.relationship_with_player
        if rel > 50:
            return f'友好 ({rel})'
        elif rel > 0:
            return f'中立偏好 ({rel})'
        elif rel > -30:
            return f'中立偏差 ({rel})'
        else:
            return f'敌对 ({rel})'

    def _fallback_response(self, player_input: str) -> str:
        """降级预设回应"""
        text = player_input.lower()

        # 匹配意图
        if any(w in text for w in ['你好', '嗨', 'hello', 'hi']):
            category = 'greeting'
        elif any(w in text for w in ['再见', '拜', 'bye']):
            category = 'farewell'
        elif self.profile.relationship_with_player < -30:
            category = 'hostile'
        elif self.profile.relationship_with_player > 50:
            category = 'friendly'
        else:
            category = 'unknown'

        return random.choice(self._fallback_responses[category])
