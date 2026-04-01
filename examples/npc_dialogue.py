# -*- coding: utf-8 -*-
"""
NPC对话示例 - 演示智能对话系统

支持两种模式:
1. 使用私有部署LLM服务 (传入llm_config或LLMClient)
2. 降级模式 (不配置LLM, 使用预设回应)
"""

from game_agent.npc.dialogue import NPCDialogueSystem, NPCProfile


def main():
    # 创建NPC档案
    profile = NPCProfile(
        name='老铁匠格兰特',
        role='铁匠',
        background='格兰特是镇上最资深的铁匠，年轻时曾是一名骑士，退役后开了这家铁匠铺。他对武器锻造有着独到的见解。',
        personality_traits=['沉稳', '寡言', '正直', '有耐心'],
        speaking_style='说话简短有力，偶尔讲述年轻时的冒险经历',
        knowledge=['武器锻造', '盔甲修理', '矿石种类', '镇上的历史', '骑士团往事'],
    )

    # ---- 方式1: 使用私有部署LLM服务 ----
    # 请根据实际环境填写, 或创建 configs/local.yaml 覆盖
    llm_config = {
        'provider': 'private',
        'model': 'your-model-name',  # 替换为你的模型名
        'base_url': 'http://your-llm-server/v1',  # 替换为你的API地址
        'api_key': 'your-api-key',  # 替换为你的API密钥
        'max_tokens': 1024,
        'temperature': 0.7,
        'timeout': 30,
    }

    # 也可以直接传入LLMClient实例:
    # client = LLMClient(llm_config)
    # dialogue = NPCDialogueSystem(npc_profile=profile, llm_client=client)

    dialogue = NPCDialogueSystem(
        npc_profile=profile,
        llm_config=llm_config,
        max_history=10,
    )

    # ---- 方式2: 降级模式(不配置LLM) ----
    # dialogue = NPCDialogueSystem(npc_profile=profile, max_history=10)

    # 游戏上下文
    game_context = {
        'location': '格兰特的铁匠铺',
        'time_of_day': '下午',
        'weather': '晴天',
        'recent_events': '最近有兽人在北方出没',
    }

    # 对话演示
    conversations = [
        '你好，老铁匠！',
        '你能帮我打造一把好剑吗？',
        '谢谢你，你真是太好了！',
        '最近镇上怎么样？',
        '再见，下次再来！',
    ]

    print(f'=== NPC对话演示: {profile.name} ===\n')

    for player_input in conversations:
        print(f'玩家: {player_input}')
        response = dialogue.generate_response(player_input, game_context)
        print(f'{profile.name}: {response}')
        print(
            f'  [情感={profile.current_emotion}, 关系={profile.relationship_with_player}]')
        print()

    # 展示对话历史
    print('--- 对话历史 ---')
    for turn in dialogue.get_history():
        tag = '玩家' if turn.role == 'player' else profile.name
        print(f'  [{tag}] {turn.content} (情感: {turn.emotion})')


if __name__ == '__main__':
    main()
