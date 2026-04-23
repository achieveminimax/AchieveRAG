"""
RAG 知识库助手 - 核心能力层

包含文档解析、文本分块、Embedding、向量存储、LLM 客户端等核心功能模块。
"""

from backend.core.document_loader import Document, DocumentLoader, load_document
from backend.core.llm_client import (
    LLMClient,
    LLMResponse,
    TokenUsage,
    get_llm_client,
    reset_llm_client,
)
from backend.core.vectorstore import (
    RetrievalResult,
    VectorStore,
    get_vectorstore,
    reset_vectorstore,
)

__all__ = [
    "Document",
    "DocumentLoader",
    "load_document",
    "LLMClient",
    "LLMResponse",
    "TokenUsage",
    "get_llm_client",
    "reset_llm_client",
    "RetrievalResult",
    "VectorStore",
    "get_vectorstore",
    "reset_vectorstore",
]
