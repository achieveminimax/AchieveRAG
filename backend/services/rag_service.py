"""
RAG 知识库助手 - RAG 问答服务模块

提供高层次的 RAG 问答服务，封装完整的对话流程：
- 对话管理（创建、加载历史）
- RAG 检索和上下文构建
- LLM 流式生成
- 消息持久化
- SSE 流式输出包装
"""

import json
import asyncio
import time
from typing import Any, AsyncGenerator, Optional

from openai import AsyncOpenAI

from backend.config.settings import Settings, get_settings
from backend.core.embeddings import EmbeddingClient, get_embedding_client
from backend.core.rag_chain import RAGChain, get_rag_chain
from backend.core.vectorstore import VectorStore, get_vectorstore
from backend.db.database import Database, get_database
from backend.models.schemas import SourceReference


class RAGService:
    """RAG 问答服务类
    
    封装完整的 RAG 问答业务流程，包括对话管理、检索、生成和持久化。
    
    Attributes:
        db: 数据库实例
        rag_chain: RAG 链路实例
        llm_client: OpenAI 异步客户端
        settings: 应用配置
    
    Example:
        >>> from backend.services.rag_service import RAGService
        >>> service = RAGService()
        >>> 
        >>> # 流式问答
        >>> async for event in service.ask("什么是 RAG？"):
        ...     print(event)
        >>> 
        >>> # 指定对话继续
        >>> async for event in service.ask("什么是 RAG？", conversation_id="conv-123"):
        ...     print(event)
    """
    
    # SSE 事件类型常量
    EVENT_TOKEN = "token"
    EVENT_SOURCES = "sources"
    EVENT_DONE = "done"
    EVENT_ERROR = "error"
    
    def __init__(
        self,
        db: Optional[Database] = None,
        rag_chain: Optional[RAGChain] = None,
        embedding_client: Optional[EmbeddingClient] = None,
        vectorstore: Optional[VectorStore] = None,
        settings: Optional[Settings] = None,
    ):
        """初始化 RAG 服务
        
        Args:
            db: 数据库实例，默认使用全局实例
            rag_chain: RAG 链路实例，默认使用全局实例
            embedding_client: Embedding 客户端，默认使用全局实例
            vectorstore: 向量存储实例，默认使用全局实例
            settings: 应用配置，默认自动加载
        """
        self._settings = settings or get_settings()
        self._db = db or get_database()
        self._rag_chain = rag_chain or get_rag_chain(
            embedding_client=embedding_client,
            vectorstore=vectorstore,
            settings=self._settings,
        )
        
        # 初始化 OpenAI 客户端（用于 LLM）
        self._llm_client = AsyncOpenAI(
            api_key=self._settings.openai_api_key,
            base_url=self._settings.openai_base_url,
        )
    
    @property
    def db(self) -> Database:
        """获取数据库实例"""
        return self._db
    
    @property
    def rag_chain(self) -> RAGChain:
        """获取 RAG 链路实例"""
        return self._rag_chain
    
    @property
    def llm_client(self) -> AsyncOpenAI:
        """获取 LLM 客户端"""
        return self._llm_client
    
    def _load_chat_history(
        self,
        conversation_id: str,
        max_rounds: Optional[int] = None,
    ) -> list[dict[str, str]]:
        """加载对话历史
        
        从数据库加载最近的对话历史，转换为 OpenAI 消息格式。
        
        Args:
            conversation_id: 对话 ID
            max_rounds: 最大历史轮数，默认使用配置值
            
        Returns:
            消息列表，格式为 [{"role": "user/assistant", "content": "..."}]
        """
        max_rounds = max_rounds or self._settings.max_chat_history
        
        # 从数据库获取最近的消息
        messages = self._db.get_recent_messages(conversation_id, n=max_rounds * 2)
        
        # 转换为 OpenAI 格式
        chat_history = []
        for msg in messages:
            if msg["role"] in ("user", "assistant"):
                chat_history.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        
        return chat_history
    
    def _create_conversation(self, title: Optional[str] = None) -> dict[str, Any]:
        """创建新对话
        
        Args:
            title: 对话标题，默认自动生成
            
        Returns:
            创建的对话记录
        """
        return self._db.create_conversation(title=title)
    
    def _save_user_message(
        self,
        conversation_id: str,
        content: str,
    ) -> dict[str, Any]:
        """保存用户消息
        
        Args:
            conversation_id: 对话 ID
            content: 消息内容
            
        Returns:
            创建的消息记录
        """
        return self._db.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
            sources=None,
        )
    
    def _save_assistant_message(
        self,
        conversation_id: str,
        content: str,
        sources: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """保存助手消息
        
        Args:
            conversation_id: 对话 ID
            content: 消息内容
            sources: 来源引用列表
            
        Returns:
            创建的消息记录
        """
        return self._db.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            sources=sources,
        )
    
    def _format_sse_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> str:
        """格式化 SSE 事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            
        Returns:
            SSE 格式的事件字符串
        """
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _build_document_filter(self, document_ids: Optional[list[str]] = None) -> Optional[dict[str, Any]]:
        """构建文档过滤条件"""
        valid_document_ids = [doc_id for doc_id in (document_ids or []) if doc_id]
        if not valid_document_ids:
            return None

        if len(valid_document_ids) == 1:
            return {"document_id": valid_document_ids[0]}

        return {
            "$or": [{"document_id": doc_id} for doc_id in valid_document_ids]
        }

    def _is_list_documents_intent(self, question: str) -> bool:
        q = (question or "").strip()
        if not q:
            return False
        q = q.replace(" ", "")
        triggers = (
            "列出我所有文档",
            "列出所有文档",
            "列出我的文档",
            "所有文档的名称",
            "所有文档名称",
            "所有文档名字",
            "我的文档有哪些",
            "有哪些文档",
            "文档列表",
            "我上传了哪些文档",
        )
        return any(t in q for t in triggers)

    def _format_document_list_answer(self, documents: list[dict[str, Any]]) -> str:
        if not documents:
            return "当前知识库暂无文档。"
        filenames = [str(d.get("filename") or "").strip() for d in documents if d.get("filename")]
        filenames = [name for name in filenames if name]
        if not filenames:
            return "当前知识库暂无可用文档。"
        lines = "\n".join(f"- {name}" for name in filenames)
        return f"当前知识库共有 {len(filenames)} 份文档：\n{lines}"
    
    async def ask(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        top_k: Optional[int] = None,
        document_ids: Optional[list[str]] = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """问答方法（流式输出）
        
        完整的 RAG 问答流程：
        1. 创建或加载对话
        2. 保存用户消息
        3. 加载对话历史
        4. 执行 RAG 检索
        5. 调用 LLM 流式生成
        6. 保存助手消息
        7. 发送完成事件
        
        Args:
            question: 用户问题
            conversation_id: 对话 ID，不传则创建新对话
            top_k: 检索文档数量，默认使用配置
            stream: 是否流式输出，当前仅支持流式
            
        Yields:
            SSE 格式的事件字符串
            
        Example:
            >>> async for event in service.ask("什么是 RAG？"):
            ...     # event 格式: "event: token\ndata: {...}\n\n"
            ...     print(event)
        """
        conversation = None
        user_message = None
        sources_data: list[dict[str, Any]] = []
        full_answer = ""
        filter_dict = self._build_document_filter(document_ids)
        
        try:
            # 1. 创建或加载对话
            if conversation_id:
                conversation = self._db.get_conversation(conversation_id)
                if not conversation:
                    # 对话不存在，创建新对话
                    conversation = self._create_conversation(title=question[:50])
                    conversation_id = conversation["id"]
            else:
                # 创建新对话，使用问题前 50 字作为标题
                conversation = self._create_conversation(title=question[:50])
                conversation_id = conversation["id"]
            
            # 2. 保存用户消息
            user_message = self._save_user_message(conversation_id, question)

            if (not document_ids) and self._is_list_documents_intent(question):
                documents = self._db.get_all_documents()
                answer = self._format_document_list_answer(documents)
                assistant_message = self._save_assistant_message(
                    conversation_id=conversation_id,
                    content=answer,
                    sources=[],
                )
                yield self._format_sse_event(
                    self.EVENT_TOKEN,
                    {"content": answer},
                )
                yield self._format_sse_event(
                    self.EVENT_DONE,
                    {
                        "conversation_id": conversation_id,
                        "message_id": assistant_message["id"],
                    },
                )
                return
            
            # 3. 加载对话历史（最近 N 轮）
            chat_history = self._load_chat_history(conversation_id)
            
            # 4. 执行 RAG 检索
            try:
                context, messages = await self._rag_chain.arun(
                    query=question,
                    chat_history=chat_history,
                    top_k=top_k,
                    filter_dict=filter_dict,
                )
                sources_data = context.sources
            except Exception as e:
                # 检索失败，发送错误事件
                yield self._format_sse_event(
                    self.EVENT_ERROR,
                    {"message": f"检索失败: {str(e)}"},
                )
                return
            
            # 5. 发送来源引用事件（在生成前发送，让前端提前展示）
            if sources_data:
                yield self._format_sse_event(
                    self.EVENT_SOURCES,
                    {"sources": sources_data},
                )
            
            # 6. 调用 LLM 流式生成
            try:
                response = await self._llm_client.chat.completions.create(
                    model=self._settings.llm_model,
                    messages=messages,
                    temperature=self._settings.llm_temperature,
                    max_tokens=self._settings.llm_max_tokens,
                    stream=True,
                )
                
                # 流式接收 token
                token_buffer: list[str] = []
                buffered_chars = 0
                last_flush = time.monotonic()
                flush_interval_s = 0.05
                max_buffer_chars = 200

                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_answer += token
                        token_buffer.append(token)
                        buffered_chars += len(token)

                        now = time.monotonic()
                        if buffered_chars >= max_buffer_chars or (now - last_flush) >= flush_interval_s:
                            batched = "".join(token_buffer)
                            token_buffer.clear()
                            buffered_chars = 0
                            last_flush = now
                            yield self._format_sse_event(
                                self.EVENT_TOKEN,
                                {"content": batched},
                            )

                if token_buffer:
                    yield self._format_sse_event(
                        self.EVENT_TOKEN,
                        {"content": "".join(token_buffer)},
                    )
                
            except asyncio.CancelledError:
                return
            except Exception as e:
                # LLM 调用失败
                yield self._format_sse_event(
                    self.EVENT_ERROR,
                    {"message": f"生成回答失败: {str(e)}"},
                )
                return
            
            # 7. 保存助手消息
            assistant_message = self._save_assistant_message(
                conversation_id=conversation_id,
                content=full_answer,
                sources=sources_data,
            )
            
            # 8. 发送完成事件
            yield self._format_sse_event(
                self.EVENT_DONE,
                {
                    "conversation_id": conversation_id,
                    "message_id": assistant_message["id"],
                },
            )
            
        except asyncio.CancelledError:
            return
        except Exception as e:
            # 全局错误处理
            yield self._format_sse_event(
                self.EVENT_ERROR,
                {"message": f"服务错误: {str(e)}"},
            )
    
    async def ask_non_stream(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        top_k: Optional[int] = None,
        document_ids: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """问答方法（非流式输出）
        
        适用于不需要流式输出的场景，直接返回完整回答。
        
        Args:
            question: 用户问题
            conversation_id: 对话 ID，不传则创建新对话
            top_k: 检索文档数量，默认使用配置
            
        Returns:
            包含 answer、sources、conversation_id 等的字典
        """
        conversation = None
        sources_data: list[dict[str, Any]] = []
        full_answer = ""
        filter_dict = self._build_document_filter(document_ids)
        
        # 1. 创建或加载对话
        if conversation_id:
            conversation = self._db.get_conversation(conversation_id)
            if not conversation:
                conversation = self._create_conversation(title=question[:50])
                conversation_id = conversation["id"]
        else:
            conversation = self._create_conversation(title=question[:50])
            conversation_id = conversation["id"]
        
        # 2. 保存用户消息
        self._save_user_message(conversation_id, question)

        if (not document_ids) and self._is_list_documents_intent(question):
            documents = self._db.get_all_documents()
            answer = self._format_document_list_answer(documents)
            assistant_message = self._save_assistant_message(
                conversation_id=conversation_id,
                content=answer,
                sources=[],
            )
            return {
                "conversation_id": conversation_id,
                "message_id": assistant_message["id"],
                "answer": answer,
                "sources": [],
            }
        
        # 3. 加载对话历史
        chat_history = self._load_chat_history(conversation_id)
        
        # 4. 执行 RAG 检索
        context, messages = await self._rag_chain.arun(
            query=question,
            chat_history=chat_history,
            top_k=top_k,
            filter_dict=filter_dict,
        )
        sources_data = context.sources
        
        # 5. 调用 LLM 非流式生成
        response = await self._llm_client.chat.completions.create(
            model=self._settings.llm_model,
            messages=messages,
            temperature=self._settings.llm_temperature,
            max_tokens=self._settings.llm_max_tokens,
            stream=False,
        )
        
        full_answer = response.choices[0].message.content or ""
        
        # 6. 保存助手消息
        assistant_message = self._save_assistant_message(
            conversation_id=conversation_id,
            content=full_answer,
            sources=sources_data,
        )
        
        return {
            "conversation_id": conversation_id,
            "message_id": assistant_message["id"],
            "answer": full_answer,
            "sources": [SourceReference(**s) for s in sources_data],
        }
    
    async def regenerate(
        self,
        conversation_id: str,
        message_id: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """重新生成回答
        
        基于历史对话重新生成最后一条回答。
        
        Args:
            conversation_id: 对话 ID
            message_id: 要重新生成的消息 ID，默认最后一条助手消息
            top_k: 检索文档数量
            
        Yields:
            SSE 格式的事件字符串
        """
        # 获取对话的所有消息
        messages = self._db.get_messages_by_conversation(conversation_id)
        
        if not messages:
            yield self._format_sse_event(
                self.EVENT_ERROR,
                {"message": "对话不存在或没有消息"},
            )
            return
        
        # 找到最后一条用户消息
        last_user_message = None
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_user_message = msg
                break
        
        if not last_user_message:
            yield self._format_sse_event(
                self.EVENT_ERROR,
                {"message": "没有找到用户问题"},
            )
            return
        
        # 重新执行问答流程
        async for event in self.ask(
            question=last_user_message["content"],
            conversation_id=conversation_id,
            top_k=top_k,
        ):
            yield event
    
    def get_conversation_history(self, conversation_id: str) -> list[dict[str, Any]]:
        """获取对话历史
        
        Args:
            conversation_id: 对话 ID
            
        Returns:
            消息列表
        """
        return self._db.get_messages_by_conversation(conversation_id)
    
    def get_stats(self) -> dict[str, Any]:
        """获取服务统计信息
        
        Returns:
            统计信息字典
        """
        rag_stats = self._rag_chain.get_stats()
        db_stats = {
            "total_conversations": len(self._db.get_all_conversations()),
            "total_documents": self._db.get_document_stats()["total_documents"],
        }
        
        return {
            "llm_model": self._settings.llm_model,
            "temperature": self._settings.llm_temperature,
            "max_tokens": self._settings.llm_max_tokens,
            **rag_stats,
            **db_stats,
        }


# 全局 RAGService 实例（单例模式）
_rag_service_instance: Optional[RAGService] = None


def get_rag_service(
    db: Optional[Database] = None,
    rag_chain: Optional[RAGChain] = None,
    embedding_client: Optional[EmbeddingClient] = None,
    vectorstore: Optional[VectorStore] = None,
    settings: Optional[Settings] = None,
) -> RAGService:
    """获取 RAGService 实例（单例模式）
    
    使用单例模式避免重复创建客户端，提高性能。
    
    Args:
        db: 数据库实例
        rag_chain: RAG 链路实例
        embedding_client: Embedding 客户端
        vectorstore: 向量存储实例
        settings: 应用配置
        
    Returns:
        RAGService 实例
        
    Example:
        >>> from backend.services.rag_service import get_rag_service
        >>> service = get_rag_service()
        >>> async for event in service.ask("什么是 RAG？"):
        ...     print(event)
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService(
            db=db,
            rag_chain=rag_chain,
            embedding_client=embedding_client,
            vectorstore=vectorstore,
            settings=settings,
        )
    return _rag_service_instance


def reset_rag_service() -> None:
    """重置全局 RAGService 实例
    
    用于测试或需要重新初始化客户端的场景。
    """
    global _rag_service_instance
    _rag_service_instance = None
