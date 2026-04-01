# -*- coding: utf-8 -*-
"""
记忆模块 - 管理Agent的短期记忆、长期记忆和情景记忆

短期记忆: 最近的感知和决策信息, 容量有限, FIFO淘汰
长期记忆: 重要的经验和知识, 按相关性检索
情景记忆: 完整的交互情景, 用于模式匹配和学习
"""

from __future__ import annotations

import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    SHORT_TERM = 'short_term'
    LONG_TERM = 'long_term'
    EPISODIC = 'episodic'


@dataclass
class MemoryEntry:
    """单条记忆"""

    content: dict[str, Any]
    memory_type: MemoryType
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5  # 重要性 [0, 1]
    access_count: int = 0  # 访问次数
    tags: list[str] = field(default_factory=list)
    memory_id: str = ''

    def __post_init__(self):
        if not self.memory_id:
            raw = f'{self.content}{self.timestamp}'
            self.memory_id = hashlib.md5(raw.encode()).hexdigest()[:12]


class AgentMemory:
    """Agent记忆系统

    支持三种记忆类型:
    - 短期记忆: 固定容量的FIFO队列, 存储最近的感知/决策
    - 长期记忆: 按重要性和相关性检索的持久化记忆
    - 情景记忆: 完整交互场景, 支持模式匹配
    """

    def __init__(
        self,
        short_term_capacity: int = 20,
        long_term_capacity: int = 1000,
        episodic_capacity: int = 500,
        relevance_threshold: float = 0.3,
    ):
        self.short_term_capacity = short_term_capacity
        self.long_term_capacity = long_term_capacity
        self.episodic_capacity = episodic_capacity
        self.relevance_threshold = relevance_threshold

        self._short_term: deque[MemoryEntry] = deque(
            maxlen=short_term_capacity)
        self._long_term: list[MemoryEntry] = []
        self._episodic: list[MemoryEntry] = []

    # ---- 存储接口 ----

    def store(
        self,
        content: dict[str, Any],
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """存储一条新记忆"""
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags or [],
        )

        if memory_type == MemoryType.SHORT_TERM:
            self._short_term.append(entry)
            # 高重要性自动升级到长期记忆
            if importance >= 0.8:
                self._promote_to_long_term(entry)
        elif memory_type == MemoryType.LONG_TERM:
            self._add_long_term(entry)
        elif memory_type == MemoryType.EPISODIC:
            self._add_episodic(entry)

        return entry

    def store_interaction(
        self,
        action: str,
        context: dict[str, Any],
        result: dict[str, Any],
        importance: float = 0.5,
    ) -> MemoryEntry:
        """存储一次完整的交互记录(感知→决策→执行)"""
        content = {
            'action': action,
            'context': context,
            'result': result,
        }
        return self.store(content, MemoryType.EPISODIC, importance, tags=['interaction'])

    # ---- 检索接口 ----

    def retrieve(
        self,
        query: dict[str, Any],
        memory_type: MemoryType | None = None,
        top_k: int = 5,
    ) -> list[MemoryEntry]:
        """根据查询条件检索相关记忆

        Args:
            query: 查询上下文(用于计算相关性)
            memory_type: 指定检索的记忆类型, None 表示全部
            top_k: 返回最相关的前k条
        """
        candidates: list[MemoryEntry] = []

        if memory_type is None or memory_type == MemoryType.SHORT_TERM:
            candidates.extend(self._short_term)
        if memory_type is None or memory_type == MemoryType.LONG_TERM:
            candidates.extend(self._long_term)
        if memory_type is None or memory_type == MemoryType.EPISODIC:
            candidates.extend(self._episodic)

        # 计算相关性分数并排序
        scored = []
        for entry in candidates:
            score = self._compute_relevance(query, entry)
            if score >= self.relevance_threshold:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for _, entry in scored[:top_k]:
            entry.access_count += 1
            results.append(entry)
        return results

    def get_recent(self, n: int = 5) -> list[MemoryEntry]:
        """获取最近n条短期记忆"""
        items = list(self._short_term)
        return items[-n:]

    def get_by_tags(self, tags: list[str], top_k: int = 10) -> list[MemoryEntry]:
        """根据标签检索记忆"""
        tag_set = set(tags)
        results = []
        for store in [self._short_term, self._long_term, self._episodic]:
            for entry in store:
                if tag_set & set(entry.tags):
                    results.append(entry)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:top_k]

    # ---- 维护接口 ----

    def clear(self, memory_type: MemoryType | None = None):
        """清空指定类型的记忆"""
        if memory_type is None or memory_type == MemoryType.SHORT_TERM:
            self._short_term.clear()
        if memory_type is None or memory_type == MemoryType.LONG_TERM:
            self._long_term.clear()
        if memory_type is None or memory_type == MemoryType.EPISODIC:
            self._episodic.clear()

    def consolidate(self):
        """记忆整合 - 将高频访问的短期记忆提升到长期记忆"""
        for entry in list(self._short_term):
            if entry.access_count >= 3 or entry.importance >= 0.7:
                self._promote_to_long_term(entry)

    @property
    def stats(self) -> dict[str, int]:
        return {
            'short_term': len(self._short_term),
            'long_term': len(self._long_term),
            'episodic': len(self._episodic),
        }

    # ---- 内部方法 ----

    def _promote_to_long_term(self, entry: MemoryEntry):
        """将记忆提升为长期记忆"""
        long_entry = MemoryEntry(
            content=entry.content,
            memory_type=MemoryType.LONG_TERM,
            timestamp=entry.timestamp,
            importance=entry.importance,
            access_count=entry.access_count,
            tags=entry.tags,
        )
        self._add_long_term(long_entry)

    def _add_long_term(self, entry: MemoryEntry):
        """添加到长期记忆, 超出容量时淘汰最不重要的"""
        self._long_term.append(entry)
        if len(self._long_term) > self.long_term_capacity:
            self._long_term.sort(key=lambda e: e.importance)
            self._long_term.pop(0)

    def _add_episodic(self, entry: MemoryEntry):
        """添加到情景记忆"""
        self._episodic.append(entry)
        if len(self._episodic) > self.episodic_capacity:
            self._episodic.pop(0)

    def _compute_relevance(self, query: dict[str, Any], entry: MemoryEntry) -> float:
        """计算查询与记忆条目的相关性分数

        基于以下因素加权:
        - 关键词重叠度 (0.4)
        - 时间衰减 (0.3)
        - 重要性 (0.2)
        - 访问频率 (0.1)
        """
        # 关键词重叠
        query_keys = set(str(v).lower() for v in query.values() if v)
        entry_keys = set(str(v).lower() for v in entry.content.values() if v)
        if query_keys and entry_keys:
            overlap = len(query_keys & entry_keys) / \
                max(len(query_keys | entry_keys), 1)
        else:
            overlap = 0.0

        # 时间衰减 (指数衰减, 半衰期1小时)
        age = time.time() - entry.timestamp
        time_score = 2.0 ** (-age / 3600.0)

        # 重要性
        importance_score = entry.importance

        # 访问频率归一化
        freq_score = min(entry.access_count / 10.0, 1.0)

        score = 0.4 * overlap + 0.3 * time_score + \
            0.2 * importance_score + 0.1 * freq_score
        return score
