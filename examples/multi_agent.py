# -*- coding: utf-8 -*-
"""
多Agent协作示例 - 演示Agent协调管理器
"""

from game_agent.coordination.coordinator import AgentCoordinator, TaskAssignmentStrategy


def main():
    print('=== 多Agent协作示例 ===\n')

    # 创建协调器
    coordinator = AgentCoordinator(
        strategy=TaskAssignmentStrategy.PRIORITY,
        communication_range=100.0,
    )

    # 注册Agent
    agents = [
        ('guard_01', 'guard', ['combat', 'patrol'], (10, 0, 10)),
        ('guard_02', 'guard', ['combat', 'patrol'], (20, 0, 15)),
        ('scout_01', 'scout', ['reconnaissance', 'stealth'], (30, 0, 5)),
        ('healer_01', 'healer', ['heal', 'support'], (15, 0, 20)),
        ('archer_01', 'archer', ['ranged_combat', 'patrol'], (25, 0, 10)),
    ]

    for aid, atype, caps, pos in agents:
        coordinator.register_agent(aid, atype, caps, pos)
        print(f'注册Agent: {aid} ({atype}), 能力={caps}')

    # 创建任务
    print('\n--- 创建任务 ---')
    t1 = coordinator.create_task(
        task_type='defend',
        position=(15, 0, 15),
        priority=10,
        required_agents=2,
        required_capabilities=['combat'],
    )
    print(f'任务1 [{t1}]: 防守据点, 需要2名战斗Agent')

    t2 = coordinator.create_task(
        task_type='scout',
        position=(50, 0, 50),
        priority=5,
        required_agents=1,
        required_capabilities=['reconnaissance'],
    )
    print(f'任务2 [{t2}]: 侦察前方, 需要1名侦察Agent')

    t3 = coordinator.create_task(
        task_type='patrol',
        position=(0, 0, 0),
        priority=3,
        required_agents=1,
        required_capabilities=['patrol'],
    )
    print(f'任务3 [{t3}]: 巡逻, 需要1名巡逻Agent')

    # 执行分配
    print('\n--- 执行任务分配 ---')
    assignments = coordinator.assign_tasks()
    for task_id, agent_ids in assignments.items():
        task = coordinator.get_task(task_id)
        print(f'任务 {task_id} ({task.task_type}): 分配给 {agent_ids}')

    # Agent间通信
    print('\n--- Agent通信 ---')
    coordinator.send_message(
        sender='scout_01',
        receiver='*',
        content={'alert': '发现敌人编队, 位置(50,0,50), 约10人'},
        msg_type='alert',
    )
    print('scout_01 广播: 发现敌人编队!')

    # 各Agent接收消息
    for aid in ['guard_01', 'guard_02', 'healer_01', 'archer_01']:
        msgs = coordinator.get_messages(aid)
        if msgs:
            for m in msgs:
                print(f'  {aid} 收到来自 {m.sender} 的{m.msg_type}: {m.content}')

    # 完成任务
    print('\n--- 完成任务 ---')
    coordinator.complete_task(t2, success=True)
    print(f'任务 {t2} 完成!')

    # 统计
    print(f'\n协调器统计: {coordinator.stats}')
    print(f'空闲Agent: {[a.agent_id for a in coordinator.get_idle_agents()]}')


if __name__ == '__main__':
    main()
