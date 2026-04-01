# Game Agent - 游戏智能Agent框架

基于 **感知-决策-执行** 循环架构的游戏智能Agent框架，支持NPC智能化对话、行为树+状态机融合决策、动态难度调整(DDA)和个性化内容生成。

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                    Game World                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Player   │  │   NPCs   │  │   Environment    │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │                 │             │
│       └──────────────┼─────────────────┘             │
│                      ▼                               │
│  ┌───────────────────────────────────────────────┐  │
│  │           Perception Module (感知层)            │  │
│  │  • 环境感知  • 玩家行为分析  • 事件监听         │  │
│  └───────────────────┬───────────────────────────┘  │
│                      ▼                               │
│  ┌───────────────────────────────────────────────┐  │
│  │            Memory Module (记忆层)               │  │
│  │  • 短期记忆  • 长期记忆  • 情景记忆             │  │
│  └───────────────────┬───────────────────────────┘  │
│                      ▼                               │
│  ┌───────────────────────────────────────────────┐  │
│  │           Decision Module (决策层)              │  │
│  │  • 行为树(BT)  • 状态机(FSM)  • LLM推理       │  │
│  └───────────────────┬───────────────────────────┘  │
│                      ▼                               │
│  ┌───────────────────────────────────────────────┐  │
│  │           Action Executor (执行层)              │  │
│  │  • 动作执行  • 对话生成  • 结果反馈             │  │
│  └───────────────────┬───────────────────────────┘  │
│                      ▼                               │
│  ┌───────────────────────────────────────────────┐  │
│  │         Experience System (体验优化层)          │  │
│  │  • DDA动态难度  • 个性化生成  • 性能优化        │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## 项目结构

```
game-agent/
├── game_agent/                  # 核心包
│   ├── __init__.py
│   ├── agent.py                 # GameAgent 主类
│   ├── core/                    # 核心模块
│   │   ├── __init__.py
│   │   ├── memory.py            # 记忆系统(短期/长期/情景)
│   │   ├── perception.py        # 感知模块
│   │   ├── decision.py          # 决策模块
│   │   └── action.py            # 行动执行器
│   ├── npc/                     # NPC智能化
│   │   ├── __init__.py
│   │   ├── dialogue.py          # NPC对话系统(LLM集成)
│   │   ├── behavior_tree.py     # 行为树实现
│   │   ├── state_machine.py     # 状态机实现
│   │   └── personality.py       # NPC性格与情感系统
│   ├── experience/              # 游戏体验优化
│   │   ├── __init__.py
│   │   ├── dda.py               # 动态难度调整
│   │   └── content_generator.py # 个性化内容生成
│   ├── optimization/            # 性能优化
│   │   ├── __init__.py
│   │   ├── async_engine.py      # 异步处理引擎
│   │   ├── cache.py             # 决策缓存
│   │   └── lod.py               # LOD层级管理
│   ├── coordination/            # 多Agent协作
│   │   ├── __init__.py
│   │   └── coordinator.py       # 协调管理器
│   └── world/                   # 游戏世界模拟
│       ├── __init__.py
│       └── game_world.py        # 游戏世界接口
├── examples/                    # 使用示例
│   ├── basic_agent.py           # 基础Agent示例
│   ├── npc_dialogue.py          # NPC对话示例
│   ├── guard_npc.py             # 守卫NPC示例(BT+FSM)
│   └── multi_agent.py           # 多Agent协作示例
├── tests/                       # 测试
│   ├── __init__.py
│   ├── test_memory.py
│   ├── test_decision.py
│   └── test_dialogue.py
├── configs/                     # 配置文件
│   └── default.yaml             # 默认配置
├── requirements.txt
├── setup.py
└── README.md
```

## 核心特性

- **分层决策架构**: 感知→记忆→决策→执行 闭环
- **LLM驱动对话**: 支持OpenAI等LLM接口，带降级策略
- **行为树+状态机**: 高层状态管理 + 细粒度行为逻辑
- **动态难度调整(DDA)**: 实时监控玩家表现，自适应调参
- **个性化内容**: 基于玩家画像生成任务和对话
- **性能优化**: 异步引擎 + 决策缓存 + LOD系统
- **多Agent协作**: 集中式协调器支持任务分配与通信

## 快速开始

```python
from game_agent import GameAgent
from game_agent.world import GameWorld

# 创建游戏世界
world = GameWorld()

# 创建Agent
agent = GameAgent(agent_id="guard_01", game_world=world, role="guard")

# Agent主循环
perception = agent.perceive()
decision = agent.decide(perception)
result = agent.execute(decision)
```

## 安装

```bash
pip install -r requirements.txt
```

## 配置

编辑 `configs/default.yaml` 配置LLM接口、性能参数等。
