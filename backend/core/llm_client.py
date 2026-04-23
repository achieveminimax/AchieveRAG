"""
RAG 知识库助手 - LLM 客户端封装模块

提供统一的 LLM 调用接口，支持同步调用、流式输出、Token 用量统计和重试机制。
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

import openai
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.config.settings import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Token 用量统计
    
    Attributes:
        prompt_tokens: 输入 Token 数量
        completion_tokens: 输出 Token 数量
        total_tokens: 总 Token 数量
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """LLM 响应结果
    
    Attributes:
        content: 生成的文本内容
        usage: Token 用量统计
        model: 使用的模型名称
        finish_reason: 完成原因
    """
    content: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: Optional[str] = None


class LLMClient:
    """LLM 客户端类
    
    封装 OpenAI API 的异步调用，提供同步和流式两种调用方式，
    支持自动重试、Token 用量统计和错误处理。
    
    Example:
        >>> client = LLMClient()
        >>> messages = [{"role": "user", "content": "你好"}]
        >>> response = await client.chat(messages)
        >>> print(response.content)
        
        >>> # 流式调用
        >>> async for token in client.stream(messages):
        ...     print(token, end="")
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """初始化 LLM 客户端
        
        Args:
            api_key: OpenAI API Key，默认从 settings 读取
            base_url: API 基础 URL，默认从 settings 读取
            model: 模型名称，默认从 settings 读取
            temperature: Temperature 参数，默认从 settings 读取
            max_tokens: 最大生成 Token 数，默认从 settings 读取
        """
        settings = get_settings()
        
        self._api_key = api_key or settings.openai_api_key
        self._base_url = base_url or settings.openai_base_url
        self._model = model or settings.llm_model
        self._temperature = temperature if temperature is not None else settings.llm_temperature
        self._max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens
        
        # 初始化 OpenAI 异步客户端
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        
        logger.info(
            f"LLMClient initialized with model={self._model}, "
            f"temperature={self._temperature}, max_tokens={self._max_tokens}"
        )
    
    @retry(
        retry=retry_if_exception_type((
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.APIConnectionError,
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """同步调用 LLM 生成回复
        
        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            temperature: 覆盖默认 temperature
            max_tokens: 覆盖默认 max_tokens
            **kwargs: 其他传递给 OpenAI API 的参数
            
        Returns:
            LLMResponse: 包含生成内容和 Token 用量的响应对象
            
        Raises:
            openai.APIError: API 调用失败（已重试后）
            ValueError: 参数校验失败
            
        Example:
            >>> messages = [
            ...     {"role": "system", "content": "你是一个助手"},
            ...     {"role": "user", "content": "你好"},
            ... ]
            >>> response = await client.chat(messages)
            >>> print(response.content)
        """
        if not messages:
            raise ValueError("messages 不能为空")
        
        temp = temperature if temperature is not None else self._temperature
        max_tok = max_tokens if max_tokens is not None else self._max_tokens
        
        try:
            logger.debug(f"Sending chat request with {len(messages)} messages")
            
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore
                temperature=temp,
                max_tokens=max_tok,
                **kwargs,
            )
            
            # 提取响应内容
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            
            # 提取 Token 用量
            usage = TokenUsage()
            if response.usage:
                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )
            
            logger.info(
                f"Chat completed: model={response.model}, "
                f"tokens={usage.total_tokens}, finish_reason={finish_reason}"
            )
            
            return LLMResponse(
                content=content,
                usage=usage,
                model=response.model,
                finish_reason=finish_reason,
            )
            
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise
        except openai.APITimeoutError as e:
            logger.warning(f"API timeout: {e}")
            raise
        except openai.APIError as e:
            logger.error(f"API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in chat: {e}")
            raise
    
    @retry(
        retry=retry_if_exception_type((
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.APIConnectionError,
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """流式调用 LLM 生成回复
        
        使用 SSE (Server-Sent Events) 方式逐 token 返回生成内容。
        
        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            temperature: 覆盖默认 temperature
            max_tokens: 覆盖默认 max_tokens
            **kwargs: 其他传递给 OpenAI API 的参数
            
        Yields:
            str: 生成的文本片段（token）
            
        Raises:
            openai.APIError: API 调用失败（已重试后）
            ValueError: 参数校验失败
            
        Example:
            >>> messages = [{"role": "user", "content": "讲个故事"}]
            >>> async for token in client.stream(messages):
            ...     print(token, end="", flush=True)
        """
        if not messages:
            raise ValueError("messages 不能为空")
        
        temp = temperature if temperature is not None else self._temperature
        max_tok = max_tokens if max_tokens is not None else self._max_tokens
        
        try:
            logger.debug(f"Starting stream with {len(messages)} messages")
            
            stream_response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore
                temperature=temp,
                max_tokens=max_tok,
                stream=True,
                **kwargs,
            )
            
            token_count = 0
            async for chunk in stream_response:
                # 提取 delta 内容
                delta = chunk.choices[0].delta
                if delta.content:
                    token_count += 1
                    yield delta.content
            
            logger.info(f"Stream completed: {token_count} tokens generated")
            
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit exceeded in stream: {e}")
            raise
        except openai.APITimeoutError as e:
            logger.warning(f"API timeout in stream: {e}")
            raise
        except openai.APIError as e:
            logger.error(f"API error in stream: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in stream: {e}")
            raise
    
    async def chat_with_stream(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> tuple[str, TokenUsage]:
        """流式调用并收集完整响应
        
        适用于需要流式输出同时又需要获取完整内容和 Token 用量的场景。
        注意：此方法无法获取精确的 Token 用量（流式 API 不返回 usage），
        completion_tokens 为估算值。
        
        Args:
            messages: 对话消息列表
            temperature: 覆盖默认 temperature
            max_tokens: 覆盖默认 max_tokens
            **kwargs: 其他传递给 OpenAI API 的参数
            
        Returns:
            tuple[str, TokenUsage]: (完整内容, Token 用量估算)
        """
        full_content = []
        prompt_tokens = self._estimate_tokens(messages)
        
        async for token in self.stream(messages, temperature, max_tokens, **kwargs):
            full_content.append(token)
        
        content = "".join(full_content)
        completion_tokens = self._estimate_tokens([{"role": "assistant", "content": content}])
        
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        
        return content, usage
    
    def _estimate_tokens(self, messages: list[dict[str, str]]) -> int:
        """估算消息列表的 Token 数量
        
        使用简单的字符估算方法（中文约 1.5 字符/token，英文约 4 字符/token）。
        这是一个粗略估算，实际 Token 数可能有所不同。
        
        Args:
            messages: 消息列表
            
        Returns:
            int: 估算的 Token 数量
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            total_chars += len(content)
        
        # 简单估算：假设平均每个 token 约 2.5 个字符
        return int(total_chars / 2.5)
    
    @property
    def model(self) -> str:
        """获取当前使用的模型名称"""
        return self._model
    
    @property
    def temperature(self) -> float:
        """获取当前 temperature 设置"""
        return self._temperature
    
    @property
    def max_tokens(self) -> int:
        """获取当前 max_tokens 设置"""
        return self._max_tokens


# 全局客户端实例（单例模式）
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取 LLM 客户端实例（单例模式）
    
    Returns:
        LLMClient: LLM 客户端实例
        
    Example:
        >>> client = get_llm_client()
        >>> response = await client.chat([{"role": "user", "content": "你好"}])
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def reset_llm_client() -> LLMClient:
    """重置并重新创建 LLM 客户端实例
    
    用于配置变更后重新初始化客户端。
    
    Returns:
        LLMClient: 新的 LLM 客户端实例
    """
    global _llm_client
    _llm_client = LLMClient()
    return _llm_client
