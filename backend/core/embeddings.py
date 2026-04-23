"""
RAG 知识库助手 - Embedding 封装模块

封装 OpenAI Embedding API，提供文本向量化功能。
支持批量嵌入、配置切换模型、错误重试等特性。
"""

import asyncio
from typing import List, Optional, Union

import openai
from openai import AsyncOpenAI

from backend.config.settings import Settings, get_settings


class EmbeddingClient:
    """Embedding 客户端封装类
    
    封装 OpenAI Embedding API，提供统一的文本向量化接口。
    支持单条和批量文本嵌入，自动处理 API 调用和错误处理。
    
    Attributes:
        client: OpenAI 异步客户端实例
        model: 当前使用的 Embedding 模型名称
        embedding_dim: 嵌入向量维度
        
    Example:
        >>> from backend.core.embeddings import EmbeddingClient
        >>> client = EmbeddingClient()
        >>> # 单条嵌入
        >>> embedding = await client.embed_query("什么是 RAG？")
        >>> # 批量嵌入
        >>> embeddings = await client.embed_documents(["文本1", "文本2", "文本3"])
    """
    
    # 支持的 Embedding 模型及其维度
    SUPPORTED_MODELS = {
        # OpenAI 模型
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        # 阿里云百炼模型
        "text-embedding-v3": 1024,
        "text-embedding-v2": 1536,
        "text-embedding-v1": 1536,
        # MiniMax 模型
        "minimax-embedding-01": 1024,
    }
    
    # 默认批量大小
    # OpenAI 限制每次最多 2048 个文本
    # 阿里云百炼限制每次最多 10 个文本
    DEFAULT_BATCH_SIZE = 128
    
    def __init__(self, settings: Optional[Settings] = None):
        """初始化 Embedding 客户端
        
        Args:
            settings: 配置实例，如果为 None 则自动加载默认配置
        """
        self._settings = settings or get_settings()
        self._client = AsyncOpenAI(
            api_key=self._settings.embedding_api_key,
            base_url=self._settings.embedding_base_url,
        )
        self._model = self._settings.embedding_model
        
        # 验证模型是否支持
        if self._model not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"不支持的 Embedding 模型: {self._model}. "
                f"支持的模型: {list(self.SUPPORTED_MODELS.keys())}"
            )
    
    @property
    def model(self) -> str:
        """获取当前使用的 Embedding 模型名称"""
        return self._model
    
    @property
    def embedding_dim(self) -> int:
        """获取当前模型的嵌入向量维度"""
        return self.SUPPORTED_MODELS.get(self._model, 1536)
    
    @property
    def client(self) -> AsyncOpenAI:
        """获取 OpenAI 客户端实例"""
        return self._client
    
    async def embed_query(self, text: str) -> List[float]:
        """对单个查询文本进行嵌入
        
        适用于用户查询的向量化，通常查询文本较短。
        
        Args:
            text: 需要嵌入的文本
            
        Returns:
            嵌入向量（浮点数列表）
            
        Raises:
            ValueError: 文本为空或过长
            openai.APIError: API 调用失败
            
        Example:
            >>> embedding = await client.embed_query("什么是 RAG 技术？")
            >>> len(embedding)
            1536
        """
        if not text or not text.strip():
            raise ValueError("文本不能为空")
        
        # OpenAI 有文本长度限制（约 8192 tokens）
        # 这里做简单检查，实际限制取决于 token 数而非字符数
        if len(text) > 100000:
            raise ValueError("文本过长，超过最大限制（100000 字符）")
        
        response = await self._client.embeddings.create(
            model=self._model,
            input=text.strip(),
            encoding_format="float",
        )
        
        return response.data[0].embedding
    
    async def embed_documents(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """对多个文档文本进行批量嵌入
        
        自动分批处理，避免单次请求过大。适用于文档分块的向量化。
        
        Args:
            texts: 需要嵌入的文本列表
            batch_size: 每批处理的文本数量，默认为 100
            show_progress: 是否显示进度（当前仅用于日志记录）
            
        Returns:
            嵌入向量列表，与输入文本一一对应
            
        Raises:
            ValueError: 文本列表为空或包含空文本
            openai.APIError: API 调用失败
            
        Example:
            >>> texts = ["RAG 是一种技术", "向量数据库用于存储", "Embedding 是文本的向量表示"]
            >>> embeddings = await client.embed_documents(texts)
            >>> len(embeddings)
            3
        """
        if not texts:
            raise ValueError("文本列表不能为空")
        
        # 清理文本（去除首尾空白）
        cleaned_texts = [t.strip() if t else "" for t in texts]
        
        # 检查空文本
        for i, text in enumerate(cleaned_texts):
            if not text:
                raise ValueError(f"第 {i+1} 个文本为空")
        
        if batch_size is None:
            if self._model.startswith("text-embedding-v"):
                batch_size = 10
            else:
                batch_size = self.DEFAULT_BATCH_SIZE
        all_embeddings: List[List[float]] = []
        
        total_batches = (len(cleaned_texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(cleaned_texts), batch_size):
            batch = cleaned_texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            if show_progress:
                print(f"处理第 {batch_num}/{total_batches} 批，共 {len(batch)} 个文本...")
            
            # 调用 API 进行批量嵌入
            retries = 5
            backoff = 0.5
            last_error: Exception | None = None

            for _ in range(retries):
                try:
                    response = await self._client.embeddings.create(
                        model=self._model,
                        input=batch,
                        encoding_format="float",
                    )
                    last_error = None
                    break
                except (
                    openai.RateLimitError,
                    openai.APITimeoutError,
                    openai.APIConnectionError,
                    openai.APIError,
                ) as e:
                    last_error = e
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 8.0)

            if last_error is not None:
                raise last_error
            
            # 提取嵌入向量（保持顺序）
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def embed_document(self, text: str) -> List[float]:
        """对单个文档文本进行嵌入（embed_query 的别名）
        
        Args:
            text: 需要嵌入的文本
            
        Returns:
            嵌入向量
        """
        return await self.embed_query(text)
    
    def sync_embed_query(self, text: str) -> List[float]:
        """同步方式对单个文本进行嵌入
        
        用于非异步环境下的简单调用。
        
        Args:
            text: 需要嵌入的文本
            
        Returns:
            嵌入向量
        """
        return asyncio.run(self.embed_query(text))
    
    def sync_embed_documents(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        """同步方式对多个文本进行批量嵌入
        
        Args:
            texts: 需要嵌入的文本列表
            batch_size: 每批处理的文本数量
            
        Returns:
            嵌入向量列表
        """
        return asyncio.run(self.embed_documents(texts, batch_size))
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """获取支持的 Embedding 模型列表
        
        Returns:
            支持的模型名称列表
        """
        return list(cls.SUPPORTED_MODELS.keys())
    
    @classmethod
    def get_model_dimension(cls, model: str) -> int:
        """获取指定模型的嵌入维度
        
        Args:
            model: 模型名称
            
        Returns:
            嵌入向量维度
            
        Raises:
            ValueError: 不支持的模型
        """
        if model not in cls.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {model}")
        return cls.SUPPORTED_MODELS[model]


# 全局客户端实例（单例模式）
_embedding_client: Optional[EmbeddingClient] = None


def get_embedding_client(settings: Optional[Settings] = None) -> EmbeddingClient:
    """获取 EmbeddingClient 实例（单例模式）
    
    使用单例模式避免重复创建客户端，提高性能。
    
    Args:
        settings: 配置实例，如果为 None 则使用默认配置
        
    Returns:
        EmbeddingClient 实例
        
    Example:
        >>> from backend.core.embeddings import get_embedding_client
        >>> client = get_embedding_client()
        >>> embedding = await client.embed_query("测试文本")
    """
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient(settings)
    return _embedding_client


def reset_embedding_client() -> None:
    """重置全局 EmbeddingClient 实例
    
    用于测试或需要重新初始化客户端的场景。
    """
    global _embedding_client
    _embedding_client = None
