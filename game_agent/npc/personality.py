"""
NPC性格与情感系统

为NPC提供情感状态管理、性格模型和社交行为驱动。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class EmotionType(str, Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"
    CURIOUS = "curious"
    GRATEFUL = "grateful"
    HOSTILE = "hostile"


@dataclass
class EmotionState:
    """情感状态, 多维度情感向量"""
    happiness: float = 0.5       # [0, 1]
    anger: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    sadness: float = 0.0
    trust: float = 0.5
    timestamp: float = field(default_factory=time.time)

    @property
    def dominant_emotion(self) -> EmotionType:
        """获取主导情感"""
        emotions = {
            EmotionType.HAPPY: self.happiness,
            EmotionType.ANGRY: self.anger,
            EmotionType.FEARFUL: self.fear,
            EmotionType.SURPRISED: self.surprise,
            EmotionType.SAD: self.sadness,
        }
        dominant = max(emotions, key=emotions.get)
        if emotions[dominant] < 0.3:
            return EmotionType.NEUTRAL
        return dominant

    def decay(self, rate: float = 0.05):
        """情感衰减 - 随时间趋向中性"""
        self.happiness = self._toward(self.happiness, 0.5, rate)
        self.anger = self._toward(self.anger, 0.0, rate)
        self.fear = self._toward(self.fear, 0.0, rate)
        self.surprise = self._toward(self.surprise, 0.0, rate)
        self.sadness = self._toward(self.sadness, 0.0, rate)
        self.timestamp = time.time()

    def apply_stimulus(self, stimulus: dict[str, float]):
        """施加情感刺激"""
        for attr, delta in stimulus.items():
            if hasattr(self, attr):
                val = getattr(self, attr)
                setattr(self, attr, max(0.0, min(1.0, val + delta)))
        self.timestamp = time.time()

    @staticmethod
    def _toward(value: float, target: float, rate: float) -> float:
        if abs(value - target) < rate:
            return target
        return value + rate * (1 if target > value else -1)


@dataclass
class PersonalityTraits:
    """五大人格模型 (Big Five)"""
    openness: float = 0.5           # 开放性
    conscientiousness: float = 0.5  # 尽责性
    extraversion: float = 0.5      # 外向性
    agreeableness: float = 0.5     # 宜人性
    neuroticism: float = 0.5       # 神经质


class NPCPersonality:
    """NPC性格系统

    基于五大人格模型 + 情感状态, 影响NPC的对话风格和行为倾向。
    """

    def __init__(
        self,
        name: str,
        traits: PersonalityTraits | None = None,
        initial_emotion: EmotionState | None = None,
    ):
        self.name = name
        self.traits = traits or PersonalityTraits()
        self.emotion = initial_emotion or EmotionState()
        self._relationships: dict[str, float] = {}  # entity_id -> relationship_score

    def get_relationship(self, entity_id: str) -> float:
        return self._relationships.get(entity_id, 0.0)

    def update_relationship(self, entity_id: str, delta: float):
        current = self._relationships.get(entity_id, 0.0)
        # 宜人性高的NPC关系变化更缓和
        modulated_delta = delta * (0.5 + 0.5 * self.traits.agreeableness)
        self._relationships[entity_id] = max(-100, min(100, current + modulated_delta))

    def react_to_event(self, event_type: str, intensity: float = 0.5) -> EmotionState:
        """对事件产生情感反应"""
        stimulus = self._event_to_stimulus(event_type, intensity)
        self.emotion.apply_stimulus(stimulus)
        return self.emotion

    def get_behavior_modifier(self) -> dict[str, float]:
        """基于当前性格和情感获取行为修正器"""
        return {
            "aggression": (self.emotion.anger * 0.6 + (1 - self.traits.agreeableness) * 0.4),
            "caution": (self.emotion.fear * 0.5 + self.traits.neuroticism * 0.3 + (1 - self.traits.openness) * 0.2),
            "sociability": (self.traits.extraversion * 0.6 + self.emotion.happiness * 0.4),
            "initiative": (self.traits.openness * 0.4 + self.traits.conscientiousness * 0.3 + self.emotion.happiness * 0.3),
        }

    def tick(self, dt: float = 1.0):
        """每帧更新, 情感自然衰减"""
        decay_rate = 0.02 * dt * (1 + self.traits.neuroticism * 0.5)
        self.emotion.decay(rate=decay_rate)

    def _event_to_stimulus(self, event_type: str, intensity: float) -> dict[str, float]:
        """将事件类型映射为情感刺激"""
        mapping = {
            "attacked":     {"anger": 0.3 * intensity, "fear": 0.2 * intensity},
            "praised":      {"happiness": 0.3 * intensity, "trust": 0.1 * intensity},
            "insulted":     {"anger": 0.4 * intensity, "sadness": 0.1 * intensity},
            "gift":         {"happiness": 0.4 * intensity, "surprise": 0.2 * intensity},
            "threat":       {"fear": 0.4 * intensity, "anger": 0.1 * intensity},
            "ally_death":   {"sadness": 0.5 * intensity, "anger": 0.2 * intensity},
            "victory":      {"happiness": 0.5 * intensity, "surprise": 0.1 * intensity},
            "unexpected":   {"surprise": 0.5 * intensity},
        }
        return mapping.get(event_type, {})
