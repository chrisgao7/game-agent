"""
基础Agent示例 - 演示感知→决策→执行循环
"""

from game_agent import GameAgent, GameWorld


def main():
    # 1. 创建游戏世界
    world = GameWorld()
    world.set_time_of_day("day")
    world.set_weather("clear")

    # 2. 注册一些实体
    world.register_entity("player_01", "player", position=(10, 0, 10), health=1.0)
    world.register_entity("enemy_01", "enemy", position=(15, 0, 12), health=0.8, state="hostile")

    # 3. 创建Agent
    agent = GameAgent(
        agent_id="guard_01",
        game_world=world,
        role="npc",
        position=(12, 0, 10),
    )

    print(f"Agent创建: {agent}")
    print(f"初始状态: {agent.stats}")

    # 4. 执行几个tick
    for i in range(5):
        print(f"\n--- Tick {i + 1} ---")
        results = agent.tick()
        for r in results:
            print(f"  行动: {r.action} -> 成功={r.success}, 耗时={r.duration:.4f}s")

        print(f"  状态: state={agent.state}, health={agent.health:.2f}")
        print(f"  记忆: {agent.memory.stats}")

    print(f"\n最终统计: {agent.stats}")


if __name__ == "__main__":
    main()
