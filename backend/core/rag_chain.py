"""
RAG 知识库助手 - RAG 链路编排模块

封装完整的 RAG（检索增强生成）流程，包括：
- Query 向量化
- ChromaDB 相似度搜索（Top-K）
- 上下文构建
- Prompt 组装
- 来源引用提取

与 LLM 客户端配合实现端到端的问答能力。
"""

from dataclasses import dataclass
from typing import Any, Optional

from backend.config.settings import Settings, get_settings
from backend.core.embeddings import EmbeddingClient, get_embedding_client
from backend.core.vectorstore import RetrievalResult, VectorStore, get_vectorstore
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RAGContext:
    """RAG 上下文数据类
    
    封装 RAG 流程中检索和构建的上下文信息。
    
    Attributes:
        query: 用户原始查询
        query_embedding: 查询向量
        retrieval_results: 检索结果列表
        context_text: 组装后的上下文文本
        sources: 来源引用列表
    """
    query: str
    query_embedding: list[float]
    retrieval_results: list[RetrievalResult]
    context_text: str
    sources: list[dict[str, Any]]


@dataclass
class RAGResponse:
    """RAG 响应数据类
    
    封装 RAG 流程的完整响应。
    
    Attributes:
        answer: AI 生成的回答
        sources: 来源引用列表
        context: RAG 上下文信息
    """
    answer: str
    sources: list[dict[str, Any]]
    context: RAGContext


class RAGChain:
    """RAG 链路编排类
    
    封装完整的 RAG 流程，协调 Embedding、向量检索、上下文构建、Prompt 组装等环节。
    
    Attributes:
        embedding_client: Embedding 客户端
        vectorstore: 向量存储实例
        settings: 应用配置
        top_k: 默认检索数量
        similarity_threshold: 相似度阈值
    
    Example:
        >>> from backend.core.rag_chain import RAGChain
        >>> rag = RAGChain()
        >>> 
        >>> # 执行检索和上下文构建
        >>> context = await rag.retrieve("什么是 RAG 技术？")
        >>> 
        >>> # 构建 Prompt
        >>> messages = rag.build_prompt(context, chat_history=[])
        >>> 
        >>> # 提取来源引用
        >>> sources = rag.extract_sources(context.retrieval_results)
    """
    
    # 默认 System Prompt 模板
    DEFAULT_SYSTEM_PROMPT_TEMPLATE = """你是一个专业的知识库问答助手。请基于以下检索到的文档内容来回答用户的问题。

规则：
1. 优先基于提供的上下文信息回答，尽量从中提取与问题相关的要点
2. 如果上下文中有部分相关信息，请尽力整合并回答，同时说明信息来源
3. 只有在上下文内容与问题完全无关时，才告知用户当前知识库中未找到相关内容
4. 回答时请引用信息来源（文件名和位置）
5. 使用清晰、简洁的语言回答
6. 如果适合，可以使用列表或表格来组织回答

检索到的上下文内容：
{context}
"""
    
    def __init__(
        self,
        embedding_client: Optional[EmbeddingClient] = None,
        vectorstore: Optional[VectorStore] = None,
        settings: Optional[Settings] = None,
    ):
        """初始化 RAG 链路
        
        Args:
            embedding_client: Embedding 客户端，默认使用全局实例
            vectorstore: 向量存储实例，默认使用全局实例
            settings: 应用配置，默认自动加载
        """
        self._settings = settings or get_settings()
        self._embedding_client = embedding_client or get_embedding_client()
        self._vectorstore = vectorstore or get_vectorstore(
            embedding_client=self._embedding_client,
            settings=self._settings,
        )
        
        # 检索配置
        self._top_k = self._settings.default_top_k
        self._similarity_threshold = self._settings.similarity_threshold
        
        # 来源多样性：初始检索倍率（实际检索 top_k * 倍率，再去重筛选）
        self._retrieval_multiplier = 3
        # 每个来源文档最多保留的 chunk 数量（多来源时生效，单来源不限制）
        # 增加限制以获取更多相关内容
        self._max_chunks_per_source = 10
        
        # System Prompt 模板
        self._system_prompt_template = self.DEFAULT_SYSTEM_PROMPT_TEMPLATE
    
    @property
    def embedding_client(self) -> EmbeddingClient:
        """获取 Embedding 客户端"""
        return self._embedding_client
    
    @property
    def vectorstore(self) -> VectorStore:
        """获取向量存储实例"""
        return self._vectorstore
    
    @property
    def top_k(self) -> int:
        """获取默认检索数量"""
        return self._top_k
    
    @top_k.setter
    def top_k(self, value: int) -> None:
        """设置默认检索数量"""
        if not 1 <= value <= 20:
            raise ValueError("top_k 必须在 1-20 之间")
        self._top_k = value
    
    @property
    def similarity_threshold(self) -> float:
        """获取相似度阈值"""
        return self._similarity_threshold
    
    @similarity_threshold.setter
    def similarity_threshold(self, value: float) -> None:
        """设置相似度阈值"""
        if not 0.0 <= value <= 1.0:
            raise ValueError("similarity_threshold 必须在 0-1 之间")
        self._similarity_threshold = value
    
    @property
    def system_prompt_template(self) -> str:
        """获取 System Prompt 模板"""
        return self._system_prompt_template
    
    @system_prompt_template.setter
    def system_prompt_template(self, template: str) -> None:
        """设置自定义 System Prompt 模板
        
        模板中必须包含 {context} 占位符。
        
        Args:
            template: 自定义模板字符串
        """
        if "{context}" not in template:
            raise ValueError("System Prompt 模板必须包含 {context} 占位符")
        self._system_prompt_template = template
    
    async def embed_query(self, query: str) -> list[float]:
        """对查询文本进行向量化
        
        Args:
            query: 用户查询文本
            
        Returns:
            查询向量
            
        Raises:
            ValueError: 查询文本为空
            RuntimeError: 向量化失败
        """
        if not query or not query.strip():
            raise ValueError("查询文本不能为空")
        
        return await self._embedding_client.embed_query(query.strip())
    
    async def similarity_search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_dict: Optional[dict[str, Any]] = None,
    ) -> list[RetrievalResult]:
        """执行相似度搜索
        
        基于查询文本检索最相似的文档片段。
        
        Args:
            query: 查询文本
            top_k: 返回结果数量，默认使用配置值
            filter_dict: 元数据过滤条件
            
        Returns:
            检索结果列表，按相似度降序排列
        """
        top_k = top_k or self._top_k
        
        results = await self._vectorstore.similarity_search(
            query=query,
            top_k=top_k,
            filter_dict=filter_dict,
        )
        
        # 应用相似度阈值过滤
        if self._similarity_threshold > 0:
            results = [
                r for r in results 
                if r.score >= self._similarity_threshold
            ]
        
        return results
    
    async def similarity_search_by_vector(
        self,
        query_embedding: list[float],
        top_k: Optional[int] = None,
        filter_dict: Optional[dict[str, Any]] = None,
    ) -> list[RetrievalResult]:
        """基于向量执行相似度搜索
        
        直接使用向量进行搜索，避免重复计算 Embedding。
        支持来源多样性优化：扩大检索范围后按来源交叉采样。
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量，默认使用配置值
            filter_dict: 元数据过滤条件
            
        Returns:
            检索结果列表，按相似度降序排列，且来源多样化
        """
        top_k = top_k or self._top_k
        
        # 扩大检索范围，获取更多候选结果用于多样性筛选
        expanded_top_k = top_k * self._retrieval_multiplier
        
        search_kwargs = {
            "top_k": expanded_top_k,
            "filter_dict": filter_dict,
        }
        if filter_dict is None:
            search_kwargs["embedding"] = query_embedding
        else:
            search_kwargs["query_embedding"] = query_embedding

        results = self._vectorstore.similarity_search_by_vector(**search_kwargs)
        
        # 应用相似度阈值过滤
        if self._similarity_threshold > 0:
            results = [
                r for r in results 
                if r.score >= self._similarity_threshold
            ]
        
        # 应用来源多样性处理
        results = self._diversify_results(results, top_k)
        
        return results
    
    def _deduplicate_results(
        self,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """对检索结果进行内容去重
        
        同一文档被多次上传后，ChromaDB 中会存在完全相同内容的重复 chunk。
        按（规范化文件名 + chunk_index）去重，只保留相似度最高的一条。
        
        Args:
            results: 原始检索结果（已按相似度排序）
            
        Returns:
            去重后的检索结果列表，保持相似度排序
        """
        seen: dict[str, RetrievalResult] = {}
        
        for r in results:
            normalized_source = self._normalize_source_name(r.source)
            chunk_index = r.chunk_index
            dedup_key = f"{normalized_source}::{chunk_index}"
            
            # 只保留最高分的（results 已按分数降序排列，首次出现即为最高分）
            if dedup_key not in seen:
                seen[dedup_key] = r
        
        deduplicated = list(seen.values())
        
        if len(deduplicated) < len(results):
            logger.info(
                f"内容去重: {len(results)} 条 → {len(deduplicated)} 条 "
                f"(去除 {len(results) - len(deduplicated)} 条重复副本)"
            )
        
        return deduplicated
    
    def _diversify_results(
        self,
        results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """对检索结果进行内容去重和来源多样性处理
        
        处理流程：
        1. 内容去重：同一文件名 + 同一 chunk_index 只保留最高分
        2. 按来源文档分组
        3. 单来源时直接返回 top_k 条（覆盖文档不同部分）
        4. 多来源时轮询（Round-Robin）采样，每个来源最多取 max_chunks_per_source 条
        5. 最终按相似度重新排序
        
        Args:
            results: 原始检索结果（已按相似度排序）
            top_k: 最终需要返回的数量
            
        Returns:
            去重且多样化后的检索结果列表
        """
        if not results:
            return results
        
        # 第一步：内容去重（消除同一文档多次上传的重复 chunk）
        results = self._deduplicate_results(results)
        
        # 去重后数量不足 top_k，全部返回
        if len(results) <= top_k:
            return results
        
        # 第二步：按规范化来源分组
        source_groups: dict[str, list[RetrievalResult]] = {}
        for r in results:
            source_key = self._normalize_source_name(r.source)
            if source_key not in source_groups:
                source_groups[source_key] = []
            source_groups[source_key].append(r)
        
        # 单来源：返回所有去重后的结果（不限制数量，确保内容完整性）
        if len(source_groups) <= 1:
            logger.info(
                f"单来源检索: 去重后 {len(results)} 条, 返回全部"
            )
            return results
        
        # 第三步：多来源轮询采样
        logger.info(
            f"来源多样性处理: 去重后 {len(results)} 条, "
            f"来自 {len(source_groups)} 个不同来源, "
            f"目标 top_k={top_k}, 每来源上限={self._max_chunks_per_source}"
        )
        
        diversified: list[RetrievalResult] = []
        # 按每组最高分排序，优先从高分来源开始采
        sorted_sources = sorted(
            source_groups.items(),
            key=lambda x: x[1][0].score,
            reverse=True,
        )
        
        source_pointers = {source: 0 for source, _ in sorted_sources}
        
        while len(diversified) < top_k:
            added_in_round = False
            for source, chunks in sorted_sources:
                if len(diversified) >= top_k:
                    break
                pointer = source_pointers[source]
                if pointer < len(chunks) and pointer < self._max_chunks_per_source:
                    diversified.append(chunks[pointer])
                    source_pointers[source] = pointer + 1
                    added_in_round = True
            
            if not added_in_round:
                break
        
        # 按相似度分数重新排序
        diversified.sort(key=lambda r: r.score, reverse=True)
        
        logger.info(
            f"多样性处理后: {len(diversified)} 条结果, "
            f"来源分布: {', '.join(f'{s}({source_pointers[s]})' for s, _ in sorted_sources if source_pointers[s] > 0)}"
        )
        
        return diversified
    
    @staticmethod
    def _normalize_source_name(source: str) -> str:
        """规范化来源文件名，去掉存储时添加的 UUID 前缀
        
        存储格式为 '{uuid}_{原始文件名}'，例如：
        '97e805ee_AI_Agent_论文.pdf' -> 'AI_Agent_论文.pdf'
        
        Args:
            source: 带 UUID 前缀的来源文件名
            
        Returns:
            去掉 UUID 前缀的原始文件名
        """
        import re
        # 匹配 8位十六进制_ 前缀模式
        match = re.match(r'^[0-9a-f]{8}_(.+)$', source)
        if match:
            return match.group(1)
        return source
    
    def build_context(self, retrieval_results: list[RetrievalResult]) -> str:
        """构建上下文文本
        
        将检索到的文档片段组装成上下文文本，供 LLM 使用。
        
        Args:
            retrieval_results: 检索结果列表
            
        Returns:
            组装后的上下文文本
        """
        if not retrieval_results:
            return "（未检索到相关文档内容）"
        
        context_parts = []
        
        for i, result in enumerate(retrieval_results, 1):
            # 构建来源标识
            source_info = result.source
            if result.page is not None:
                source_info += f" (第 {result.page} 页)"
            
            # 构建片段文本
            part = f"[文档 {i}] 来源：{source_info}\n{result.text}\n"
            context_parts.append(part)
        
        return "\n".join(context_parts)
    
    def extract_sources(
        self,
        retrieval_results: list[RetrievalResult],
    ) -> list[dict[str, Any]]:
        """提取来源引用信息
        
        从检索结果中提取来源引用信息，用于前端展示。
        
        Args:
            retrieval_results: 检索结果列表
            
        Returns:
            来源引用列表，每个包含 source、page、score、text
        """
        sources = []
        
        for result in retrieval_results:
            source = {
                "source": result.source,
                "document_id": result.document_id,
                "page": result.page,
                "score": round(result.score, 4),
                "text": result.text[:500] if result.text else "",  # 限制文本长度
            }
            sources.append(source)
        
        return sources
    
    def build_prompt(
        self,
        context: RAGContext,
        chat_history: Optional[list[dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> list[dict[str, str]]:
        """构建 LLM 对话消息列表
        
        组装 System Prompt + Context + Chat History + Question。
        
        Args:
            context: RAG 上下文（包含检索结果和上下文文本）
            chat_history: 对话历史，格式为 [{"role": "user/assistant", "content": "..."}]
            system_prompt: 自定义 System Prompt，默认使用模板
            
        Returns:
            OpenAI 格式的消息列表
        """
        messages = []
        
        # 1. System Prompt
        if system_prompt:
            system_content = system_prompt.format(context=context.context_text)
        else:
            system_content = self._system_prompt_template.format(
                context=context.context_text
            )
        
        messages.append({"role": "system", "content": system_content})
        
        # 2. Chat History
        if chat_history:
            for msg in chat_history:
                # 只保留 user 和 assistant 角色
                if msg.get("role") in ("user", "assistant"):
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })
        
        # 3. Current Question
        messages.append({"role": "user", "content": context.query})
        
        return messages
    
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_dict: Optional[dict[str, Any]] = None,
    ) -> RAGContext:
        """执行检索流程
        
        完整的检索流程：Query 向量化 -> 相似度搜索（含多样性优化） -> 上下文构建 -> 来源提取。
        
        Args:
            query: 用户查询
            top_k: 检索数量
            filter_dict: 过滤条件
            
        Returns:
            RAG 上下文对象
        """
        logger.info(f"开始检索: query='{query}', top_k={top_k or self._top_k}")
        
        # 1. Query 向量化
        query_embedding = await self.embed_query(query)
        
        # 2. 相似度搜索（内部已包含来源多样性处理）
        retrieval_results = await self.similarity_search_by_vector(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_dict=filter_dict,
        )
        
        # 调试日志：输出检索结果摘要
        for i, r in enumerate(retrieval_results[:5]):
            logger.debug(
                f"检索结果 [{i+1}] 来源={r.source}, "
                f"页码={r.page}, 分数={r.score:.4f}"
            )
        
        # 3. 构建上下文文本
        context_text = self.build_context(retrieval_results)
        
        # 4. 提取来源引用
        sources = self.extract_sources(retrieval_results)
        
        return RAGContext(
            query=query,
            query_embedding=query_embedding,
            retrieval_results=retrieval_results,
            context_text=context_text,
            sources=sources,
        )
    
    async def arun(
        self,
        query: str,
        chat_history: Optional[list[dict[str, str]]] = None,
        top_k: Optional[int] = None,
        filter_dict: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
    ) -> tuple[RAGContext, list[dict[str, str]]]:
        """异步执行完整 RAG 流程（不含 LLM 调用）
        
        执行检索并构建 Prompt，返回上下文和消息列表供 LLM 使用。
        
        Args:
            query: 用户查询
            chat_history: 对话历史
            top_k: 检索数量
            filter_dict: 过滤条件
            system_prompt: 自定义 System Prompt
            
        Returns:
            (RAGContext, messages) 元组
        """
        # 执行检索
        context = await self.retrieve(
            query=query,
            top_k=top_k,
            filter_dict=filter_dict,
        )
        
        # 构建 Prompt
        messages = self.build_prompt(
            context=context,
            chat_history=chat_history,
            system_prompt=system_prompt,
        )
        
        return context, messages
    
    def get_stats(self) -> dict[str, Any]:
        """获取 RAG 相关统计信息
        
        Returns:
            统计信息字典
        """
        vector_stats = self._vectorstore.get_stats()
        
        return {
            "top_k": self._top_k,
            "similarity_threshold": self._similarity_threshold,
            "embedding_model": self._embedding_client.model,
            "embedding_dim": self._embedding_client.embedding_dim,
            **vector_stats,
        }


# 全局 RAGChain 实例（单例模式）
_rag_chain_instance: Optional[RAGChain] = None


def get_rag_chain(
    embedding_client: Optional[EmbeddingClient] = None,
    vectorstore: Optional[VectorStore] = None,
    settings: Optional[Settings] = None,
) -> RAGChain:
    """获取 RAGChain 实例（单例模式）
    
    使用单例模式避免重复创建客户端，提高性能。
    
    Args:
        embedding_client: Embedding 客户端
        vectorstore: 向量存储实例
        settings: 应用配置
        
    Returns:
        RAGChain 实例
        
    Example:
        >>> from backend.core.rag_chain import get_rag_chain
        >>> rag = get_rag_chain()
        >>> context = await rag.retrieve("什么是 RAG？")
    """
    global _rag_chain_instance
    if _rag_chain_instance is None:
        _rag_chain_instance = RAGChain(
            embedding_client=embedding_client,
            vectorstore=vectorstore,
            settings=settings,
        )
    return _rag_chain_instance


def reset_rag_chain() -> None:
    """重置全局 RAGChain 实例
    
    用于测试或需要重新初始化客户端的场景。
    """
    global _rag_chain_instance
    _rag_chain_instance = None
