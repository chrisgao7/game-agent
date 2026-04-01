# -*- coding: utf-8 -*-
"""
守卫NPC示例 - 演示行为树+状态机融合

守卫的行为:
- 空闲时巡逻
- 发现可疑活动→进入警戒状态
- 发现敌人→进入战斗状态
- 生命值低→撤退
"""

from game_agent.npc.behavior_tree import (
    ActionNode,
    BehaviorStatus,
    BehaviorTree,
    ConditionNode,
    SelectorNode,
    SequenceNode,
)
from game_agent.npc.state_machine import State, StateMachine, Transition


def create_patrol_tree() -> BehaviorTree:
    """创建巡逻行为树"""
    root = SelectorNode(
        'patrol_selector',
        [
            # 序列1: 检查到可疑活动 → 调查
            SequenceNode(
                'investigate_sequence',
                [
                    ConditionNode(
                        'is_suspicious', lambda ctx: ctx.get(
                            'suspicious_activity', False)
                    ),
                    ActionNode(
                        'investigate',
                        lambda ctx: (
                            print('    [巡逻] 发现可疑活动, 前去调查...'),
                            BehaviorStatus.SUCCESS,
                        )[-1],
                    ),
                ],
            ),
            # 序列2: 正常巡逻
            SequenceNode(
                'normal_patrol',
                [
                    ActionNode(
                        'walk_patrol',
                        lambda ctx: (print('    [巡逻] 沿巡逻路线行走...'), BehaviorStatus.SUCCESS)[
                            -1
                        ],
                    ),
                    ActionNode(
                        'look_around',
                        lambda ctx: (
                            print('    [巡逻] 环顾四周...'), BehaviorStatus.SUCCESS)[-1],
                    ),
                ],
            ),
        ],
    )
    return BehaviorTree(root, name='patrol_bt')


def create_alert_tree() -> BehaviorTree:
    """创建警戒行为树"""
    root = SelectorNode(
        'alert_selector',
        [
            # 发现敌人 → 准备战斗
            SequenceNode(
                'prepare_combat',
                [
                    ConditionNode('enemy_spotted', lambda ctx: ctx.get(
                        'enemy_visible', False)),
                    ActionNode(
                        'draw_weapon',
                        lambda ctx: (
                            print('    [警戒] 拔出武器!'), BehaviorStatus.SUCCESS)[-1],
                    ),
                    ActionNode(
                        'call_reinforcement',
                        lambda ctx: (
                            print('    [警戒] 呼叫增援!'), BehaviorStatus.SUCCESS)[-1],
                    ),
                ],
            ),
            # 继续警戒
            ActionNode(
                'stay_alert',
                lambda ctx: (print('    [警戒] 保持高度警惕...'),
                             BehaviorStatus.SUCCESS)[-1],
            ),
        ],
    )
    return BehaviorTree(root, name='alert_bt')


def create_combat_tree() -> BehaviorTree:
    """创建战斗行为树"""
    root = SelectorNode(
        'combat_selector',
        [
            # 生命值低 → 撤退
            SequenceNode(
                'retreat_sequence',
                [
                    ConditionNode('low_health', lambda ctx: ctx.get(
                        'health', 1.0) < 0.3),
                    ActionNode(
                        'retreat',
                        lambda ctx: (print('    [战斗] 生命危急, 撤退!'), BehaviorStatus.SUCCESS)[
                            -1
                        ],
                    ),
                ],
            ),
            # 正常战斗
            SequenceNode(
                'attack_sequence',
                [
                    ConditionNode('has_target', lambda ctx: ctx.get(
                        'enemy_visible', False)),
                    ActionNode(
                        'attack_enemy',
                        lambda ctx: (
                            print('    [战斗] 攻击敌人!'), BehaviorStatus.SUCCESS)[-1],
                    ),
                ],
            ),
            # 寻找掩护
            ActionNode(
                'find_cover',
                lambda ctx: (print('    [战斗] 寻找掩护...'),
                             BehaviorStatus.SUCCESS)[-1],
            ),
        ],
    )
    return BehaviorTree(root, name='combat_bt')


def main():
    print('=== 守卫NPC示例: 行为树 + 状态机 ===\n')

    # 创建状态机
    fsm = StateMachine('guard_fsm')

    # 添加状态(每个状态绑定一棵行为树)
    fsm.add_state(
        State(
            'patrol',
            behavior_tree=create_patrol_tree(),
            on_enter=lambda ctx: print('  >> 进入巡逻状态'),
        )
    )
    fsm.add_state(
        State(
            'alert',
            behavior_tree=create_alert_tree(),
            on_enter=lambda ctx: print('  >> 进入警戒状态'),
        )
    )
    fsm.add_state(
        State(
            'combat',
            behavior_tree=create_combat_tree(),
            on_enter=lambda ctx: print('  >> 进入战斗状态'),
        )
    )

    # 添加状态转移规则
    fsm.add_transition(
        Transition(
            from_state='patrol',
            to_state='alert',
            priority=10,
            condition=lambda ctx: ctx.get('suspicious_activity', False),
        )
    )
    fsm.add_transition(
        Transition(
            from_state='alert',
            to_state='combat',
            priority=20,
            condition=lambda ctx: ctx.get('enemy_visible', False),
        )
    )
    fsm.add_transition(
        Transition(
            from_state='combat',
            to_state='patrol',
            priority=5,
            condition=lambda ctx: (
                not ctx.get('enemy_visible', False) and ctx.get(
                    'health', 1.0) > 0.5
            ),
        )
    )
    fsm.add_transition(
        Transition(
            from_state='alert',
            to_state='patrol',
            priority=5,
            condition=lambda ctx: (
                not ctx.get('suspicious_activity', False) and not ctx.get(
                    'enemy_visible', False)
            ),
        )
    )

    # 设置初始状态
    fsm.set_initial_state('patrol')

    # 模拟场景
    scenarios = [
        {'label': '正常巡逻', 'suspicious_activity': False,
            'enemy_visible': False, 'health': 1.0},
        {
            'label': '发现可疑动静',
            'suspicious_activity': True,
            'enemy_visible': False,
            'health': 1.0,
        },
        {'label': '发现敌人!', 'suspicious_activity': True,
            'enemy_visible': True, 'health': 0.8},
        {'label': '战斗中', 'suspicious_activity': True,
            'enemy_visible': True, 'health': 0.5},
        {'label': '重伤!', 'suspicious_activity': True,
            'enemy_visible': True, 'health': 0.2},
        {'label': '敌人消失', 'suspicious_activity': False,
            'enemy_visible': False, 'health': 0.6},
    ]

    for i, ctx in enumerate(scenarios):
        print(f"\n--- 场景 {i + 1}: {ctx['label']} ---")
        print(
            f"  上下文: health={ctx['health']}, suspicious={ctx['suspicious_activity']}, enemy={ctx['enemy_visible']}"
        )
        fsm.update(ctx)
        print(f'  当前状态: {fsm.current_state}')

    print(f'\n状态历史: {fsm.get_history()}')


if __name__ == '__main__':
    main()
