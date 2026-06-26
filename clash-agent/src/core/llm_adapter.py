"""
LLM适配器 - 支持本地Ollama和DeepSeek API
增强版：重试机制、指数退避、空响应处理
"""

from abc import ABC, abstractmethod
from typing import Optional
import time
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
            content = result.get("message", {}).get("content", "")
            if not content or not content.strip():
                raise ValueError("LLM返回空响应")
            return content
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
                    content = result.get("message", {}).get("content", "")
                    if not content or not content.strip():
                        raise ValueError("LLM返回空响应")
                    return content
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
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content or not content.strip():
                raise ValueError("LLM返回空响应")
            return content
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
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if not content or not content.strip():
                        raise ValueError("LLM返回空响应")
                    return content
        except Exception as e:
            logger.error(f"DeepSeek API异步请求失败: {e}")
            raise


class RetryableLLM:
    """带重试机制的LLM包装器"""

    def __init__(self, adapter: BaseLLMAdapter, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
        self.adapter = adapter
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def chat(self, messages: list[dict], **kwargs) -> str:
        """带重试的对话"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = self.adapter.chat(messages, **kwargs)
                if result and result.strip():
                    if attempt > 0:
                        logger.info(f"LLM调用成功，重试次数: {attempt}")
                    return result
                else:
                    raise ValueError("LLM返回空响应")
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"LLM调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}，{delay}秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"LLM调用最终失败 (共 {self.max_retries} 次尝试): {e}")

        raise last_error

    async def achat(self, messages: list[dict], **kwargs) -> str:
        """带重试的异步对话"""
        import asyncio
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = await self.adapter.achat(messages, **kwargs)
                if result and result.strip():
                    if attempt > 0:
                        logger.info(f"LLM异步调用成功，重试次数: {attempt}")
                    return result
                else:
                    raise ValueError("LLM返回空响应")
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"LLM异步调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}，{delay}秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM异步调用最终失败 (共 {self.max_retries} 次尝试): {e}")

        raise last_error


class LLMManager:
    """LLM管理器 - 支持多后端自动切换 + 重试机制"""

    def __init__(self, config: dict = None):
        self.config = config or LLM_CONFIG
        self.adapters: dict[str, RetryableLLM] = {}
        self._init_adapters()

    def _init_adapters(self):
        """初始化可用的适配器（包装重试机制）"""
        max_retries = self.config.get("max_retries", 3)
        base_delay = self.config.get("retry_base_delay", 1.0)
        max_delay = self.config.get("retry_max_delay", 10.0)

        if self.config.get("local_enabled"):
            try:
                adapter = LocalLLMAdapter()
                self.adapters["local"] = RetryableLLM(adapter, max_retries, base_delay, max_delay)
                logger.info("Local LLM适配器初始化成功")
            except Exception as e:
                logger.warning(f"Local LLM适配器初始化失败: {e}")

        if self.config.get("deepseek_enabled") and self.config.get("deepseek_api_key"):
            try:
                adapter = DeepSeekAdapter()
                self.adapters["deepseek"] = RetryableLLM(adapter, max_retries, base_delay, max_delay)
                logger.info("DeepSeek API适配器初始化成功")
            except Exception as e:
                logger.warning(f"DeepSeek API适配器初始化失败: {e}")

        if not self.adapters:
            logger.warning("没有可用的LLM适配器")

    def chat(self, messages: list[dict], preferred: str = None) -> str:
        """
        对话接口 - 自动切换后端 + 重试

        Args:
            messages: 消息列表
            preferred: 优先使用的适配器名称

        Returns:
            LLM响应内容
        """
        if preferred and preferred in self.adapters:
            try:
                return self.adapters[preferred].chat(messages)
            except Exception as e:
                logger.warning(f"优先适配器 {preferred} 失败: {e}")

        for name in ["local", "deepseek"]:
            if name in self.adapters:
                try:
                    logger.info(f"尝试使用 {name} 适配器")
                    return self.adapters[name].chat(messages)
                except Exception as e:
                    logger.warning(f"适配器 {name} 失败: {e}")

        raise RuntimeError("所有LLM后端均不可用")

    async def achat(self, messages: list[dict], preferred: str = None) -> str:
        """异步对话接口"""
        if preferred and preferred in self.adapters:
            try:
                return await self.adapters[preferred].achat(messages)
            except Exception as e:
                logger.warning(f"优先适配器 {preferred} 失败: {e}")

        for name in ["local", "deepseek"]:
            if name in self.adapters:
                try:
                    logger.info(f"尝试使用 {name} 适配器")
                    return await self.adapters[name].achat(messages)
                except Exception as e:
                    logger.warning(f"适配器 {name} 失败: {e}")

        raise RuntimeError("所有LLM后端均不可用")

    def list_adapters(self) -> list[str]:
        """列出可用的适配器"""
        return list(self.adapters.keys())

    def is_available(self) -> bool:
        """检查是否有可用的适配器"""
        return len(self.adapters) > 0
