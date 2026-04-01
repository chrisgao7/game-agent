# -*- coding: utf-8 -*-
"""记忆模块测试"""

from game_agent.core.memory import AgentMemory, MemoryEntry, MemoryType


class TestAgentMemory:
    def setup_method(self):
        self.memory = AgentMemory(
            short_term_capacity=5,
            long_term_capacity=10,
            episodic_capacity=10,
            relevance_threshold=0.0,
        )

    def test_store_short_term(self):
        entry = self.memory.store(
            {'event': 'saw_player'}, MemoryType.SHORT_TERM)
        assert isinstance(entry, MemoryEntry)
        assert self.memory.stats['short_term'] == 1

    def test_short_term_capacity(self):
        for i in range(10):
            self.memory.store({'event': f'event_{i}'}, MemoryType.SHORT_TERM)
        # 容量为5, 只保留最新5条
        assert self.memory.stats['short_term'] == 5

    def test_auto_promote_high_importance(self):
        self.memory.store({'event': 'critical'},
                          MemoryType.SHORT_TERM, importance=0.9)
        # 高重要性自动提升
        assert self.memory.stats['long_term'] >= 1

    def test_retrieve(self):
        self.memory.store(
            {'type': 'combat', 'enemy': 'wolf'}, MemoryType.SHORT_TERM, tags=['combat']
        )
        self.memory.store(
            {'type': 'social', 'npc': 'merchant'}, MemoryType.SHORT_TERM, tags=['social']
        )

        results = self.memory.retrieve({'type': 'combat'}, top_k=5)
        assert len(results) > 0

    def test_get_recent(self):
        for i in range(3):
            self.memory.store({'event': f'recent_{i}'}, MemoryType.SHORT_TERM)
        recent = self.memory.get_recent(2)
        assert len(recent) == 2

    def test_get_by_tags(self):
        self.memory.store({'a': 1}, MemoryType.SHORT_TERM, tags=['combat'])
        self.memory.store({'b': 2}, MemoryType.SHORT_TERM, tags=['social'])
        results = self.memory.get_by_tags(['combat'])
        assert len(results) == 1

    def test_store_interaction(self):
        entry = self.memory.store_interaction(
            action='attack', context={'target': 'wolf'}, result={'success': True}
        )
        assert entry.memory_type == MemoryType.EPISODIC
        assert self.memory.stats['episodic'] == 1

    def test_clear(self):
        self.memory.store({'a': 1}, MemoryType.SHORT_TERM)
        self.memory.store({'b': 2}, MemoryType.LONG_TERM)
        self.memory.clear(MemoryType.SHORT_TERM)
        assert self.memory.stats['short_term'] == 0
        assert self.memory.stats['long_term'] == 1

    def test_consolidate(self):
        self.memory.store({'a': 1}, MemoryType.SHORT_TERM, importance=0.8)
        self.memory.consolidate()
        assert self.memory.stats['long_term'] >= 1
