"""
LLM适配器 - 支持本地Ollama和DeepSeek API
"""

from abc import ABC, abstractmethod
from typing import Optional
import requests
import json

from config.settings import LLM_CONFIG
from src.utils.logger import get_logger

logger = get_logger()


class BaseLLMAdapter(ABC):
    """LLM适配器抽象基类"""

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        """同步对话接口"""
        pass

    @abstractmethod
    async def achat(self, messages: list[dict], **kwargs) -> str:
        """异步对话接口"""
        pass


class LocalLLMAdapter(BaseLLMAdapter):
    """本地LLM适配器 - 支持Ollama兼容API"""

    def __init__(
        self,
        base_url: str = None,
        model: str = None
    ):
        self.base_url = (base_url or LLM_CONFIG["local_url"]).rstrip("/")
        self.model = model or LLM_CONFIG["local_model"]
        self.timeout = LLM_CONFIG.get("timeout", 120)

    def chat(self, messages: list[dict], **kwargs) -> str:
        """调用Ollama兼容API"""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False
                },
                timeout=kwargs.get("timeout", self.timeout)
            )
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except requests.exceptions.RequestException as e:
            logger.error(f"Local LLM请求失败: {e}")
            raise

    async def achat(self, messages: list[dict], **kwargs) -> str:
        """异步调用Ollama兼容API"""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False
                    },
                    timeout=aiohttp.ClientTimeout(total=kwargs.get("timeout", self.timeout))
                ) as response:
                    result = await response.json()
                    return result.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Local LLM异步请求失败: {e}")
            raise


class DeepSeekAdapter(BaseLLMAdapter):
    """DeepSeek API适配器"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None
    ):
        self.api_key = api_key or LLM_CONFIG["deepseek_api_key"]
        self.base_url = (base_url or LLM_CONFIG["deepseek_base_url"]).rstrip("/")
        self.model = "deepseek-chat"
        self.timeout = LLM_CONFIG.get("timeout", 60)

    def chat(self, messages: list[dict], **kwargs) -> str:
        """调用DeepSeek API"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": LLM_CONFIG.get("temperature", 0.0),
                    "max_tokens": LLM_CONFIG.get("max_tokens", 2048)
                },
                timeout=kwargs.get("timeout", self.timeout)
            )
            response.raise_for_status()
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API请求失败: {e}")
            raise

    async def achat(self, messages: list[dict], **kwargs) -> str:
        """异步调用DeepSeek API"""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": LLM_CONFIG.get("temperature", 0.0),
                        "max_tokens": LLM_CONFIG.get("max_tokens", 2048)
                    },
                    timeout=aiohttp.ClientTimeout(total=kwargs.get("timeout", self.timeout))
                ) as response:
                    result = await response.json()
                    return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"DeepSeek API异步请求失败: {e}")
            raise


class LLMManager:
    """LLM管理器 - 支持多后端自动切换"""

    def __init__(self, config: dict = None):
        self.config = config or LLM_CONFIG
        self.adapters: dict[str, BaseLLMAdapter] = {}
        self._init_adapters()

    def _init_adapters(self):
        """初始化可用的适配器"""
        # 初始化本地LLM
        if self.config.get("local_enabled"):
            try:
                self.adapters["local"] = LocalLLMAdapter()
                logger.info("Local LLM适配器初始化成功")
            except Exception as e:
                logger.warning(f"Local LLM适配器初始化失败: {e}")

        # 初始化DeepSeek
        if self.config.get("deepseek_enabled") and self.config.get("deepseek_api_key"):
            try:
                self.adapters["deepseek"] = DeepSeekAdapter()
                logger.info("DeepSeek API适配器初始化成功")
            except Exception as e:
                logger.warning(f"DeepSeek API适配器初始化失败: {e}")

        if not self.adapters:
            logger.warning("没有可用的LLM适配器")

    def chat(self, messages: list[dict], preferred: str = None) -> str:
        """
        对话接口

        Args:
            messages: 消息列表
            preferred: 优先使用的适配器名称

        Returns:
            LLM响应内容
        """
        # 如果指定了优先适配器且可用
        if preferred and preferred in self.adapters:
            try:
                return self.adapters[preferred].chat(messages)
            except Exception as e:
                logger.warning(f"优先适配器 {preferred} 失败: {e}")

        # 按优先级尝试所有适配器
        for name in ["local", "deepseek"]:
            if name in self.adapters:
                try:
                    logger.info(f"尝试使用 {name} 适配器")
                    return self.adapters[name].chat(messages)
                except Exception as e:
                    logger.warning(f"适配器 {name} 失败: {e}")

        raise RuntimeError("所有LLM后端均不可用")

    def list_adapters(self) -> list[str]:
        """列出可用的适配器"""
        return list(self.adapters.keys())

    def is_available(self) -> bool:
        """检查是否有可用的适配器"""
        return len(self.adapters) > 0
