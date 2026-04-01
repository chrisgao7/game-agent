"""
个性化内容生成 - 基于玩家画像动态生成任务和对话

系统组件:
- 玩家画像(等级/职业/偏好/风格)
- 任务模板系统
- 基于关系的对话模板
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlayerProfile:
    """玩家画像"""
    player_id: str
    level: int = 1
    class_type: str = "warrior"     # warrior / mage / rogue / healer
    play_style: str = "balanced"    # aggressive / explorer / diplomat / balanced
    preferred_activities: list[str] = field(default_factory=lambda: ["combat"])
    completed_quests: dict[str, int] = field(default_factory=dict)  # type -> count
    achievements: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuestTemplate:
    """任务模板"""
    quest_type: str              # combat / exploration / social / puzzle / collection
    title_template: str
    description_template: str
    objectives: list[dict[str, Any]]
    rewards: dict[str, Any]
    difficulty_range: tuple[int, int] = (1, 10)
    required_level: int = 1


@dataclass
class GeneratedQuest:
    """生成的任务"""
    quest_id: str
    title: str
    description: str
    quest_type: str
    objectives: list[dict[str, Any]]
    rewards: dict[str, Any]
    difficulty: int
    personalization_reason: str  # 为什么推荐这个任务


class PersonalizedContentGenerator:
    """个性化内容生成器

    根据玩家画像生成符合其偏好的任务和对话。
    """

    def __init__(self):
        self._quest_templates: dict[str, list[QuestTemplate]] = {}
        self._dialogue_templates: dict[str, dict[str, list[str]]] = {}
        self._setup_default_templates()

    # ---- 任务生成 ----

    def generate_quest(self, player: PlayerProfile) -> GeneratedQuest:
        """为玩家生成个性化任务"""
        # 确定任务类型
        quest_type = self._determine_preferred_quest_type(player)

        # 选择模板
        templates = self._quest_templates.get(quest_type, [])
        if not templates:
            templates = self._quest_templates.get("combat", [])
        template = random.choice(templates)

        # 生成参数
        params = self._generate_quest_parameters(player, template)

        # 填充模板
        quest = GeneratedQuest(
            quest_id=f"quest_{player.player_id}_{random.randint(1000, 9999)}",
            title=template.title_template.format(**params),
            description=template.description_template.format(**params),
            quest_type=quest_type,
            objectives=self._fill_objectives(template.objectives, params),
            rewards=self._scale_rewards(template.rewards, player.level),
            difficulty=params.get("difficulty", player.level),
            personalization_reason=f"Based on play_style={player.play_style}, preferred={quest_type}",
        )
        return quest

    def generate_quests(self, player: PlayerProfile, count: int = 3) -> list[GeneratedQuest]:
        """为玩家生成多个任务"""
        quests = []
        used_types = set()
        for _ in range(count):
            quest = self.generate_quest(player)
            # 尝试多样化
            attempts = 0
            while quest.quest_type in used_types and attempts < 5:
                quest = self.generate_quest(player)
                attempts += 1
            used_types.add(quest.quest_type)
            quests.append(quest)
        return quests

    # ---- 对话生成 ----

    def generate_dialogue(
        self,
        npc_role: str,
        relationship_level: float,
        context: str = "general",
    ) -> str:
        """生成个性化NPC对话"""
        # 确定关系等级
        if relationship_level > 50:
            rel_key = "friendly"
        elif relationship_level < -30:
            rel_key = "hostile"
        else:
            rel_key = "neutral"

        templates = self._dialogue_templates.get(npc_role, {}).get(rel_key, [])
        if not templates:
            templates = self._dialogue_templates.get("default", {}).get(rel_key, ["..."])

        return random.choice(templates)

    # ---- 模板管理 ----

    def add_quest_template(self, template: QuestTemplate):
        self._quest_templates.setdefault(template.quest_type, []).append(template)

    def add_dialogue_templates(self, npc_role: str, relationship: str, templates: list[str]):
        self._dialogue_templates.setdefault(npc_role, {}).setdefault(relationship, []).extend(templates)

    # ---- 内部逻辑 ----

    def _determine_preferred_quest_type(self, player: PlayerProfile) -> str:
        """根据玩家画像确定偏好的任务类型"""
        # 风格权重
        style_weights = {
            "aggressive": {"combat": 3, "exploration": 1, "social": 0, "puzzle": 1, "collection": 1},
            "explorer":   {"combat": 1, "exploration": 3, "social": 1, "puzzle": 2, "collection": 2},
            "diplomat":   {"combat": 0, "exploration": 1, "social": 3, "puzzle": 2, "collection": 1},
            "balanced":   {"combat": 2, "exploration": 2, "social": 1, "puzzle": 1, "collection": 1},
        }
        weights = style_weights.get(player.play_style, style_weights["balanced"])

        # 叠加历史完成度 (少做的类型权重增加)
        for qt in weights:
            done_count = player.completed_quests.get(qt, 0)
            if done_count < 3:
                weights[qt] += 1

        # 加权随机
        types = list(weights.keys())
        w = [max(0, weights[t]) for t in types]
        total = sum(w)
        if total == 0:
            return "combat"
        return random.choices(types, weights=w, k=1)[0]

    def _generate_quest_parameters(
        self,
        player: PlayerProfile,
        template: QuestTemplate,
    ) -> dict[str, Any]:
        """根据玩家等级和模板生成任务参数"""
        level = player.level
        difficulty = max(template.difficulty_range[0], min(template.difficulty_range[1], level))

        locations = ["黑暗森林", "迷失沼泽", "龙脊山", "古老神殿", "风暴海岸", "地下墓穴"]
        enemies = {
            "combat": ["哥布林", "骷髅兵", "暗影狼", "石像鬼", "堕落骑士"],
            "exploration": ["迷路的旅人", "神秘商人"],
            "social": ["村长", "铁匠", "旅店老板"],
        }

        return {
            "difficulty": difficulty,
            "enemy_count": max(1, difficulty // 2),
            "enemy_type": random.choice(enemies.get(template.quest_type, enemies["combat"])),
            "location": random.choice(locations),
            "item_name": f"Lv.{level}奖励装备",
            "npc_name": random.choice(["艾德里安", "塞拉", "格兰特", "莉莉安"]),
            "level": level,
        }

    def _fill_objectives(
        self,
        objectives: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        filled = []
        for obj in objectives:
            new_obj = {}
            for k, v in obj.items():
                if isinstance(v, str):
                    new_obj[k] = v.format(**params)
                elif isinstance(v, int) and k == "count":
                    new_obj[k] = max(1, v * params.get("difficulty", 1) // 3)
                else:
                    new_obj[k] = v
            filled.append(new_obj)
        return filled

    def _scale_rewards(self, rewards: dict[str, Any], level: int) -> dict[str, Any]:
        scaled = {}
        for k, v in rewards.items():
            if isinstance(v, (int, float)):
                scaled[k] = int(v * (1 + level * 0.2))
            else:
                scaled[k] = v
        return scaled

    def _setup_default_templates(self):
        """设置默认模板"""
        # 战斗任务
        self._quest_templates["combat"] = [
            QuestTemplate(
                quest_type="combat",
                title_template="讨伐{location}的{enemy_type}",
                description_template="在{location}出现了{enemy_count}只{enemy_type}，请前去消灭它们。",
                objectives=[
                    {"type": "kill", "target": "{enemy_type}", "count": 5},
                ],
                rewards={"gold": 100, "exp": 200},
            ),
            QuestTemplate(
                quest_type="combat",
                title_template="{location}的守护者",
                description_template="{npc_name}请求你前往{location}击退入侵的{enemy_type}。",
                objectives=[
                    {"type": "kill", "target": "{enemy_type}", "count": 3},
                    {"type": "survive", "description": "存活完成战斗"},
                ],
                rewards={"gold": 150, "exp": 250, "item": "random_weapon"},
            ),
        ]

        # 探索任务
        self._quest_templates["exploration"] = [
            QuestTemplate(
                quest_type="exploration",
                title_template="探索{location}",
                description_template="深入{location}，发现隐藏的秘密。据说那里藏着一件{item_name}。",
                objectives=[
                    {"type": "explore", "location": "{location}"},
                    {"type": "collect", "item": "hidden_treasure", "count": 1},
                ],
                rewards={"gold": 80, "exp": 300},
            ),
        ]

        # 社交任务
        self._quest_templates["social"] = [
            QuestTemplate(
                quest_type="social",
                title_template="{npc_name}的委托",
                description_template="{npc_name}需要你帮忙传递一封信到{location}。",
                objectives=[
                    {"type": "talk_to", "target": "{npc_name}"},
                    {"type": "deliver", "item": "letter", "destination": "{location}"},
                ],
                rewards={"gold": 60, "exp": 150, "reputation": 10},
            ),
        ]

        # 收集任务
        self._quest_templates["collection"] = [
            QuestTemplate(
                quest_type="collection",
                title_template="收集{location}的材料",
                description_template="在{location}采集稀有材料，用于锻造{item_name}。",
                objectives=[
                    {"type": "collect", "item": "rare_material", "count": 5},
                ],
                rewards={"gold": 70, "exp": 180},
            ),
        ]

        # 默认对话模板
        self._dialogue_templates["default"] = {
            "friendly": [
                "老朋友！今天也精神焕发啊。",
                "有什么需要帮忙的尽管说！",
                "我这里新到了一些好东西，要看看吗？",
            ],
            "neutral": [
                "你好，需要什么？",
                "有什么事？",
                "欢迎光临。",
            ],
            "hostile": [
                "你最好离远点。",
                "我没什么好跟你说的。",
                "又是你...想干什么？",
            ],
        }

        self._dialogue_templates["merchant"] = {
            "friendly": [
                "大主顾来了！今天给你打个折。",
                "最近进了些稀有货物，留给你了。",
            ],
            "neutral": ["看看有什么需要的吧。", "买卖公平，童叟无欺。"],
            "hostile": ["价格翻倍，爱买不买。", "别碰我的货。"],
        }

        self._dialogue_templates["guard"] = {
            "friendly": ["城里最近很安全，有你的功劳。", "辛苦了，勇士。"],
            "neutral": ["注意安全，这里最近不太平。", "站住，让我看看你的通行证。"],
            "hostile": ["我盯着你呢，别想搞事。", "再靠近一步我就不客气了。"],
        }
