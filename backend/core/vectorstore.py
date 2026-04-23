"""
RAG 知识库助手 - ChromaDB 向量存储封装模块

封装 ChromaDB 向量数据库操作，提供文档存储、相似度搜索、删除、统计等功能。
支持持久化存储，与 SQLite 元数据表关联。

主要功能：
- 初始化 ChromaDB Collection
- 添加文档（带向量和元数据）
- 相似度搜索（基于向量或文本）
- 按来源删除文档
- 获取统计信息
"""

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings

from backend.config.settings import Settings, get_settings
from backend.core.embeddings import EmbeddingClient


@dataclass
class RetrievalResult:
    """检索结果数据类
    
    封装单次检索返回的文档片段及其元数据。
    
    Attributes:
        text: 检索到的文本内容
        source: 来源文件名
        page: 页码（如适用）
        score: 相似度分数（余弦相似度，越高越相似）
        chunk_index: 分块序号
        document_id: 关联的文档 ID
        metadata: 完整的元数据字典
    """
    text: str
    source: str
    page: Optional[int] = None
    score: float = 0.0
    chunk_index: int = 0
    document_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class VectorStore:
    """ChromaDB 向量存储封装类
    
    封装 ChromaDB 的所有操作，提供统一的向量存储和检索接口。
    支持持久化存储，自动管理 Collection 生命周期。
    
    Attributes:
        client: ChromaDB 客户端实例
        collection: ChromaDB Collection 实例
        embedding_client: Embedding 客户端实例
        persist_directory: 持久化目录路径
    
    Example:
        >>> from backend.core.vectorstore import VectorStore
        >>> from backend.core.embeddings import EmbeddingClient
        >>> 
        >>> # 初始化
        >>> embedding_client = EmbeddingClient()
        >>> vectorstore = VectorStore(embedding_client=embedding_client)
        >>> 
        >>> # 添加文档
        >>> chunks = [
        ...     {"text": "RAG 是一种技术", "metadata": {"source": "doc.pdf", "page": 1}},
        ...     {"text": "向量数据库用于存储", "metadata": {"source": "doc.pdf", "page": 2}},
        ... ]
        >>> await vectorstore.add_documents(chunks)
        >>> 
        >>> # 相似度搜索
        >>> results = await vectorstore.similarity_search("什么是 RAG？", top_k=5)
        >>> for r in results:
        ...     print(f"{r.source} (p{r.page}): {r.text[:50]}...")
    """
    
    # 默认 Collection 名称
    DEFAULT_COLLECTION_NAME = "knowledge_base"
    
    # 默认距离度量方式（余弦相似度）
    DEFAULT_DISTANCE_METRIC = "cosine"

    DEFAULT_ADD_BATCH_SIZE = 500
    
    def __init__(
        self,
        embedding_client: Optional[EmbeddingClient] = None,
        persist_directory: Optional[Path] = None,
        collection_name: Optional[str] = None,
        settings: Optional[Settings] = None,
    ):
        """初始化向量存储
        
        Args:
            embedding_client: Embedding 客户端实例，用于文本向量化
            persist_directory: ChromaDB 持久化目录，默认从配置读取
            collection_name: Collection 名称，默认 "knowledge_base"
            settings: 应用配置实例，默认自动加载
        
        Raises:
            RuntimeError: ChromaDB 初始化失败
        """
        self._settings = settings or get_settings()
        self._embedding_client = embedding_client
        self._persist_directory = persist_directory or self._settings.chroma_persist_dir
        self._collection_name = collection_name or self.DEFAULT_COLLECTION_NAME
        
        # 确保持久化目录存在
        self._persist_directory.mkdir(parents=True, exist_ok=True)
        
        try:
            # 初始化 ChromaDB 客户端（持久化模式）
            self._client = chromadb.PersistentClient(
                path=str(self._persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,  # 禁用匿名遥测
                ),
            )
            
            # 获取或创建 Collection
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": self.DEFAULT_DISTANCE_METRIC},
            )
        except Exception as e:
            raise RuntimeError(f"ChromaDB 初始化失败: {e}") from e
    
    @property
    def client(self) -> chromadb.Client:
        """获取 ChromaDB 客户端实例"""
        return self._client
    
    @property
    def collection(self) -> Collection:
        """获取 ChromaDB Collection 实例"""
        return self._collection
    
    @property
    def embedding_client(self) -> Optional[EmbeddingClient]:
        """获取 Embedding 客户端实例"""
        return self._embedding_client
    
    @property
    def persist_directory(self) -> Path:
        """获取持久化目录路径"""
        return self._persist_directory
    
    async def add_documents(
        self,
        documents: list[dict[str, Any]],
        embeddings: Optional[list[list[float]]] = None,
    ) -> list[str]:
        """添加文档到向量库
        
        将文档分块及其向量添加到 ChromaDB。如果未提供 embeddings，
        则使用 embedding_client 自动计算。
        
        Args:
            documents: 文档列表，每个文档为字典，包含：
                - text: 文本内容（必需）
                - metadata: 元数据字典（可选），应包含 source、page、chunk_index 等
            embeddings: 预计算的嵌入向量列表，与 documents 一一对应
        
        Returns:
            添加的文档 ID 列表
        
        Raises:
            ValueError: 文档格式无效或 embeddings 长度不匹配
            RuntimeError: 添加文档失败
        
        Example:
            >>> chunks = [
            ...     {
            ...         "text": "RAG 是一种检索增强生成技术",
            ...         "metadata": {
            ...             "source": "rag_intro.pdf",
            ...             "page": 1,
            ...             "chunk_index": 0,
            ...             "document_id": "doc-uuid-1"
            ...         }
            ...     }
            ... ]
            >>> ids = await vectorstore.add_documents(chunks)
        """
        if not documents:
            return []
        
        # 验证文档格式
        for i, doc in enumerate(documents):
            if "text" not in doc:
                raise ValueError(f"第 {i+1} 个文档缺少 'text' 字段")
            if not doc["text"] or not doc["text"].strip():
                raise ValueError(f"第 {i+1} 个文档的 text 为空")
        
        # 生成文档 ID
        ids = [str(uuid.uuid4()) for _ in documents]
        
        # 提取文本和元数据
        texts = [doc["text"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]
        
        # 确保元数据包含必要字段
        for i, metadata in enumerate(metadatas):
            if "source" not in metadata:
                metadata["source"] = "unknown"
        
        try:
            # 如果没有提供 embeddings，则自动计算
            if embeddings is None:
                if self._embedding_client is None:
                    raise ValueError(
                        "未提供 embeddings 且未设置 embedding_client，无法计算向量"
                    )
                embeddings = await self._embedding_client.embed_documents(texts)
            
            # 验证 embeddings 长度
            if len(embeddings) != len(documents):
                raise ValueError(
                    f"embeddings 数量 ({len(embeddings)}) 与 documents 数量 ({len(documents)}) 不匹配"
                )
            
            batch_size = self.DEFAULT_ADD_BATCH_SIZE
            for i in range(0, len(ids), batch_size):
                j = i + batch_size
                self._collection.add(
                    ids=ids[i:j],
                    embeddings=embeddings[i:j],
                    documents=texts[i:j],
                    metadatas=metadatas[i:j],
                )
            
            return ids
        except Exception as e:
            raise RuntimeError(f"添加文档到向量库失败: {e}") from e
    
    async def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[dict[str, Any]] = None,
    ) -> list[RetrievalResult]:
        """相似度搜索
        
        基于查询文本的向量表示，检索最相似的文档片段。
        
        Args:
            query: 查询文本
            top_k: 返回的最相似结果数量，默认 5
            filter_dict: 元数据过滤条件，例如 {"source": "doc.pdf"}
        
        Returns:
            检索结果列表，按相似度降序排列
        
        Raises:
            ValueError: 查询文本为空或未设置 embedding_client
            RuntimeError: 搜索失败
        
        Example:
            >>> results = await vectorstore.similarity_search("什么是 RAG？", top_k=3)
            >>> for r in results:
            ...     print(f"Score: {r.score:.4f}, Source: {r.source}")
        """
        if not query or not query.strip():
            raise ValueError("查询文本不能为空")
        
        if self._embedding_client is None:
            raise ValueError("未设置 embedding_client，无法计算查询向量")
        
        try:
            # 计算查询向量
            query_embedding = await self._embedding_client.embed_query(query)
            
            # 执行相似度搜索
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_dict,
                include=["documents", "metadatas", "distances"],
            )
            
            # 解析结果
            retrieval_results = []
            
            # results 格式: {"ids": [[...]], "documents": [[...]], "metadatas": [[...]], "distances": [[...]]}
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    text = results["documents"][0][i] if results["documents"] else ""
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0.0
                    
                    # 将距离转换为相似度分数（余弦距离 -> 余弦相似度）
                    # ChromaDB 使用余弦距离，范围 [0, 2]，0 表示完全相同
                    # 转换为相似度：1 - distance/2，范围 [0, 1]
                    score = 1.0 - (distance / 2.0)
                    
                    result = RetrievalResult(
                        text=text,
                        source=metadata.get("source", "unknown"),
                        page=metadata.get("page"),
                        score=score,
                        chunk_index=metadata.get("chunk_index", 0),
                        document_id=metadata.get("document_id"),
                        metadata=metadata,
                    )
                    retrieval_results.append(result)
            
            return retrieval_results
        except Exception as e:
            raise RuntimeError(f"相似度搜索失败: {e}") from e
    
    def similarity_search_by_vector(
        self,
        query_embedding: Optional[list[float]] = None,
        *,
        embedding: Optional[list[float]] = None,
        top_k: int = 5,
        filter_dict: Optional[dict[str, Any]] = None,
    ) -> list[RetrievalResult]:
        """基于向量的相似度搜索
        
        直接使用向量进行搜索，无需 Embedding 客户端。
        
        Args:
            query_embedding: 查询向量
            embedding: 查询向量别名，兼容旧调用
            top_k: 返回的最相似结果数量，默认 5
            filter_dict: 元数据过滤条件
        
        Returns:
            检索结果列表，按相似度降序排列
        
        Raises:
            ValueError: 向量为空
            RuntimeError: 搜索失败
        
        Example:
            >>> query_embedding = [0.1, 0.2, ...]  # 预计算的向量
            >>> results = vectorstore.similarity_search_by_vector(query_embedding, top_k=5)
        """
        query_vector = query_embedding if query_embedding is not None else embedding

        if not query_vector:
            raise ValueError("查询向量不能为空")
        
        try:
            # 执行相似度搜索
            results = self._collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=filter_dict,
                include=["documents", "metadatas", "distances"],
            )
            
            # 解析结果
            retrieval_results = []
            
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    text = results["documents"][0][i] if results["documents"] else ""
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0.0
                    
                    # 将距离转换为相似度分数
                    score = 1.0 - (distance / 2.0)
                    
                    result = RetrievalResult(
                        text=text,
                        source=metadata.get("source", "unknown"),
                        page=metadata.get("page"),
                        score=score,
                        chunk_index=metadata.get("chunk_index", 0),
                        document_id=metadata.get("document_id"),
                        metadata=metadata,
                    )
                    retrieval_results.append(result)
            
            return retrieval_results
        except Exception as e:
            raise RuntimeError(f"向量搜索失败: {e}") from e
    
    def delete_by_source(self, source: str) -> int:
        """按来源删除文档
        
        删除所有指定来源的文档片段。通常用于删除某个文件的所有索引。
        
        Args:
            source: 来源文件名
        
        Returns:
            删除的文档数量
        
        Raises:
            RuntimeError: 删除失败
        
        Example:
            >>> deleted_count = vectorstore.delete_by_source("old_document.pdf")
            >>> print(f"删除了 {deleted_count} 个文档片段")
        """
        try:
            # 先查询有多少文档
            results = self._collection.get(
                where={"source": source},
                include=[],
            )
            
            count = len(results["ids"]) if results["ids"] else 0
            
            if count > 0:
                # 执行删除
                self._collection.delete(where={"source": source})
            
            return count
        except Exception as e:
            raise RuntimeError(f"删除文档失败: {e}") from e
    
    def delete_by_document_id(self, document_id: str) -> int:
        """按文档 ID 删除文档
        
        删除所有关联到指定 document_id 的文档片段。
        
        Args:
            document_id: 文档 ID（SQLite 中的 documents.id）
        
        Returns:
            删除的文档数量
        
        Example:
            >>> deleted_count = vectorstore.delete_by_document_id("doc-uuid-123")
        """
        try:
            results = self._collection.get(
                where={"document_id": document_id},
                include=[],
            )
            
            count = len(results["ids"]) if results["ids"] else 0
            
            if count > 0:
                self._collection.delete(where={"document_id": document_id})
            
            return count
        except Exception as e:
            raise RuntimeError(f"删除文档失败: {e}") from e
    
    def get_stats(self) -> dict[str, Any]:
        """获取向量库统计信息
        
        Returns:
            统计信息字典，包含：
                - total_chunks: 总分块数
                - total_documents: 不同来源文档数
                - sources: 来源文件列表
        
        Example:
            >>> stats = vectorstore.get_stats()
            >>> print(f"总分块数: {stats['total_chunks']}")
            >>> print(f"来源文档: {', '.join(stats['sources'])}")
        """
        try:
            # 获取所有文档（只包含元数据）
            results = self._collection.get(include=["metadatas"])
            
            total_chunks = len(results["ids"]) if results["ids"] else 0
            
            # 统计不同来源
            sources = set()
            if results["metadatas"]:
                for metadata in results["metadatas"]:
                    if metadata and "source" in metadata:
                        sources.add(metadata["source"])
            
            return {
                "total_chunks": total_chunks,
                "total_documents": len(sources),
                "sources": sorted(list(sources)),
            }
        except Exception as e:
            raise RuntimeError(f"获取统计信息失败: {e}") from e
    
    def get_document_chunks(self, source: str) -> list[dict[str, Any]]:
        """获取指定来源的所有文档片段
        
        Args:
            source: 来源文件名
        
        Returns:
            文档片段列表，每个包含 id、text、metadata
        
        Example:
            >>> chunks = vectorstore.get_document_chunks("doc.pdf")
            >>> for chunk in chunks:
            ...     print(f"Chunk {chunk['metadata']['chunk_index']}: {chunk['text'][:50]}")
        """
        try:
            results = self._collection.get(
                where={"source": source},
                include=["documents", "metadatas"],
            )
            
            chunks = []
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"]):
                    chunk = {
                        "id": doc_id,
                        "text": results["documents"][i] if results["documents"] else "",
                        "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    }
                    chunks.append(chunk)
            
            # 按 chunk_index 排序
            chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
            
            return chunks
        except Exception as e:
            raise RuntimeError(f"获取文档片段失败: {e}") from e
    
    def clear(self) -> int:
        """清空向量库
        
        删除 Collection 中的所有文档。
        
        Returns:
            删除的文档数量
        
        Example:
            >>> deleted = vectorstore.clear()
            >>> print(f"清空了 {deleted} 个文档片段")
        """
        try:
            # 获取当前文档数量
            stats = self.get_stats()
            count = stats["total_chunks"]
            
            if count > 0:
                # 获取所有文档 ID 并删除
                results = self._collection.get(include=[])
                if results["ids"]:
                    self._collection.delete(ids=results["ids"])
            
            return count
        except Exception as e:
            raise RuntimeError(f"清空向量库失败: {e}") from e
    
    def reset_collection(self) -> None:
        """重置 Collection
        
        删除并重新创建 Collection，用于完全重置向量库。
        
        Example:
            >>> vectorstore.reset_collection()  # 完全重置向量库
        """
        try:
            # 删除现有 Collection
            self._client.delete_collection(name=self._collection_name)
            
            # 重新创建
            self._collection = self._client.create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": self.DEFAULT_DISTANCE_METRIC},
            )
        except Exception as e:
            raise RuntimeError(f"重置 Collection 失败: {e}") from e


# 全局 VectorStore 实例（单例模式）
_vectorstore_instance: Optional[VectorStore] = None


def get_vectorstore(
    embedding_client: Optional[EmbeddingClient] = None,
    settings: Optional[Settings] = None,
) -> VectorStore:
    """获取 VectorStore 实例（单例模式）
    
    使用单例模式避免重复创建客户端，提高性能。
    
    Args:
        embedding_client: Embedding 客户端实例
        settings: 应用配置实例
    
    Returns:
        VectorStore 实例
    
    Example:
        >>> from backend.core.vectorstore import get_vectorstore
        >>> vectorstore = get_vectorstore()
        >>> results = await vectorstore.similarity_search("查询文本")
    """
    global _vectorstore_instance
    if _vectorstore_instance is None:
        _vectorstore_instance = VectorStore(
            embedding_client=embedding_client,
            settings=settings,
        )
    return _vectorstore_instance


def reset_vectorstore() -> None:
    """重置全局 VectorStore 实例
    
    用于测试或需要重新初始化客户端的场景。
    """
    global _vectorstore_instance
    _vectorstore_instance = None
