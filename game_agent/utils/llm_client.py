"""
LLM客户端 - 统一的大语言模型调用接口

支持:
- OpenAI官方API (openai协议)
- 私有部署的OpenAI兼容服务 (如vLLM, TGI, 自建推理服务等)
- 自动降级与错误处理
- 同步/流式调用
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "openai"                    # openai / private
    model: str = "gpt-3.5-turbo"
    api_key: str = ""
    base_url: str = ""                          # API地址
    max_tokens: int = 512
    temperature: float = 0.7
    timeout: int = 30
    extra_headers: dict[str, str] = field(default_factory=dict)
    extra_cookies: str = ""

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> LLMConfig:
        """从字典创建配置"""
        return cls(
            provider=config.get("provider", "openai"),
            model=config.get("model", "gpt-3.5-turbo"),
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", ""),
            max_tokens=config.get("max_tokens", 512),
            temperature=config.get("temperature", 0.7),
            timeout=config.get("timeout", 30),
            extra_headers=config.get("extra_headers", {}),
            extra_cookies=config.get("extra_cookies", ""),
        )


class LLMClient:
    """统一的LLM调用客户端

    支持OpenAI官方和私有部署的OpenAI协议兼容服务。
    通过 requests 库直接发送HTTP请求, 不依赖 openai SDK。
    """

    # OpenAI官方API默认地址
    OPENAI_BASE_URL = "https://api.openai.com/v1"

    def __init__(self, config: LLMConfig | dict[str, Any] | None = None):
        if config is None:
            self.config = LLMConfig()
        elif isinstance(config, dict):
            self.config = LLMConfig.from_dict(config)
        else:
            self.config = config

        self._session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """配置HTTP会话"""
        headers = {
            "Content-Type": "application/json",
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        # 合并自定义headers
        headers.update(self.config.extra_headers)

        self._session.headers.update(headers)

        if self.config.extra_cookies:
            self._session.headers["Cookie"] = self.config.extra_cookies

    @property
    def _chat_url(self) -> str:
        """获取 chat completions 端点URL"""
        base = self.config.base_url.rstrip("/") if self.config.base_url else self.OPENAI_BASE_URL
        # 如果base_url已经包含/v1, 不重复添加
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        elif "/v1/" in base:
            # base_url可能已经是完整路径
            return base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        else:
            return f"{base}/v1/chat/completions"

    def chat(
        self,
        user_message: str,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
        **kwargs,
    ) -> str | None:
        """简单的聊天接口

        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            history: 对话历史 [{"role": "user"/"assistant", "content": "..."}]
            **kwargs: 覆盖默认参数(model, temperature, max_tokens等)

        Returns:
            LLM回复文本, 失败返回None
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        return self.chat_completions(messages, **kwargs)

    def chat_completions(
        self,
        messages: list[dict[str, str]],
        **kwargs,
    ) -> str | None:
        """OpenAI兼容的Chat Completions调用

        Args:
            messages: 消息列表 [{"role": "system"/"user"/"assistant", "content": "..."}]
            **kwargs: 覆盖默认参数

        Returns:
            assistant回复文本, 失败返回None
        """
        payload = {
            "model": kwargs.get("model", self.config.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": False,
        }

        try:
            response = self._session.post(
                self._chat_url,
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip() if content else None

        except requests.exceptions.Timeout:
            logger.warning("LLM request timed out (timeout=%ds)", self.config.timeout)
            return None
        except requests.exceptions.ConnectionError as e:
            logger.warning("LLM connection error: %s", e)
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning("LLM HTTP error: %s, response: %s", e, e.response.text[:200] if e.response else "")
            return None
        except (KeyError, IndexError) as e:
            logger.warning("LLM response parse error: %s", e)
            return None
        except Exception as e:
            logger.warning("LLM unexpected error: %s", e)
            return None

    def chat_completions_raw(
        self,
        messages: list[dict[str, str]],
        **kwargs,
    ) -> dict[str, Any] | None:
        """返回原始JSON响应(用于需要token用量等元数据的场景)"""
        payload = {
            "model": kwargs.get("model", self.config.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": False,
        }

        try:
            response = self._session.post(
                self._chat_url,
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("LLM raw request error: %s", e)
            return None

    def is_available(self) -> bool:
        """检测LLM服务是否可用"""
        try:
            result = self.chat("ping", max_tokens=5, temperature=0)
            return result is not None
        except Exception:
            return False

    def close(self):
        """关闭HTTP会话"""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self):
        return (
            f"LLMClient(provider={self.config.provider}, "
            f"model={self.config.model}, "
            f"base_url={self._chat_url})"
        )
