"""
决策缓存 - 基于状态哈希缓存战术决策, 减少重复计算

特性:
- 状态哈希: 将感知数据转换为可哈希的key
- TTL过期: 缓存条目自动过期
- LRU淘汰: 容量满时淘汰最久未使用的条目
"""

from __future__ import annotations

import time
import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: float = 5.0       # 生存时间(秒)

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


class DecisionCache:
    """决策缓存

    缓存Agent的战术级决策结果, 避免在相同/相似状态下重复计算。
    使用状态哈希作为key, 支持TTL过期和LRU淘汰。
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 5.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, state: dict[str, Any]) -> Optional[Any]:
        """查询缓存

        Args:
            state: 当前游戏状态(会被哈希化为key)

        Returns:
            缓存的决策结果, 未命中返回None
        """
        key = self._hash_state(state)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            self._cache.pop(key)
            self._misses += 1
            return None

        # 命中: 更新访问信息, 移到末尾(LRU)
        entry.last_accessed = time.time()
        entry.access_count += 1
        self._cache.move_to_end(key)
        self._hits += 1
        return entry.value

    def put(self, state: dict[str, Any], value: Any, ttl: float | None = None):
        """写入缓存"""
        key = self._hash_state(state)
        entry = CacheEntry(
            key=key,
            value=value,
            ttl=ttl if ttl is not None else self.default_ttl,
        )
        self._cache[key] = entry
        self._cache.move_to_end(key)

        # 淘汰
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def invalidate(self, state: dict[str, Any]):
        """使指定状态的缓存失效"""
        key = self._hash_state(state)
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired_keys:
            self._cache.pop(key)
        return len(expired_keys)

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self.hit_rate:.2%}",
        }

    def _hash_state(self, state: dict[str, Any]) -> str:
        """将状态字典转换为稳定的哈希key"""
        # 规范化: 排序key, 转JSON, 取MD5
        try:
            normalized = json.dumps(state, sort_keys=True, default=str)
        except (TypeError, ValueError):
            normalized = str(sorted(state.items()))
        return hashlib.md5(normalized.encode()).hexdigest()
