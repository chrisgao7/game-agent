# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name='game-agent',
    version='0.1.0',
    description='游戏智能Agent框架 - NPC智能化与游戏体验提升',
    author='GameAI Team',
    packages=find_packages(),
    python_requires='>=3.9',
    install_requires=[
        'requests>=2.28.0',
        'pyyaml>=6.0',
        'numpy>=1.24.0',
        'pydantic>=2.0.0',
        'aiohttp>=3.9.0',
    ],
)
