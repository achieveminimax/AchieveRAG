"""
RAG 知识库助手 - 业务服务层

提供高层次的业务逻辑封装，协调 Core 层组件完成具体业务功能。
"""

from backend.services.rag_service import RAGService, get_rag_service

__all__ = [
    "RAGService",
    "get_rag_service",
]
