"""
RAG 知识库助手 - 聊天问答路由模块

提供问答相关的 API 端点，包括：
- SSE 流式问答接口
- 同步问答接口
- 重新生成回答接口

所有接口均使用 FastAPI 的依赖注入模式，通过 RAGService 处理业务逻辑。
"""

import json
import asyncio
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.rag_service import RAGService, get_rag_service
from backend.utils.logger import get_logger

# 创建路由实例
router = APIRouter(prefix="/api/chat", tags=["Chat"])

# 获取日志记录器
logger = get_logger(__name__)


def get_rag_service_dependency():
    """获取 RAGService 的依赖函数
    
    包装 get_rag_service 以避免 FastAPI 解析其参数类型。
    """
    return get_rag_service()


async def _stream_rag_events(event_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """包装 SSE 事件流，确保异常转为 error 事件返回"""
    try:
        iterator = event_stream.__aiter__()
        while True:
            try:
                event = await asyncio.wait_for(iterator.__anext__(), timeout=15.0)
                yield event
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
            except StopAsyncIteration:
                break
            except asyncio.CancelledError:
                logger.info("SSE 连接已断开")
                return
    except Exception as exc:
        logger.error(f"SSE 流处理失败: {exc}", exc_info=True)
        yield f'event: error\ndata: {json.dumps({"message": str(exc)}, ensure_ascii=False)}\n\n'


async def event_generator(
    rag_service: Any,
    question: str,
    conversation_id: str | None = None,
    top_k: int | None = None,
    document_ids: list[str] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """将 RAGService 的 SSE 字符串流转换为结构化事件"""
    try:
        async for raw_event in rag_service.ask(
            question=question,
            conversation_id=conversation_id,
            top_k=top_k,
            document_ids=document_ids,
        ):
            event_name = "message"
            event_data: dict[str, Any] = {}

            for line in raw_event.strip().splitlines():
                if line.startswith("event: "):
                    event_name = line[7:].strip()
                elif line.startswith("data: "):
                    payload = line[6:].strip()
                    try:
                        event_data = json.loads(payload)
                    except json.JSONDecodeError:
                        event_data = {"raw": payload}

            yield {
                "event": event_name,
                "data": event_data,
            }
    except Exception as exc:
        yield {
            "event": "error",
            "data": {"message": str(exc)},
        }





@router.post("/ask", response_class=StreamingResponse)
async def chat_ask_stream(
    request: ChatRequest,
    rag_service: Any = Depends(get_rag_service_dependency),
) -> StreamingResponse:
    """流式问答接口（SSE）

    接收用户问题，通过 SSE 流式返回 AI 回答。
    支持对话历史续接，可通过 conversation_id 指定已有对话。

    Args:
        request: 聊天请求数据，包含 question、conversation_id、top_k 等
        rag_service: RAG 服务实例（依赖注入）

    Returns:
        EventSourceResponse: SSE 流式响应

    SSE 事件类型:
        - token: 生成的文本片段，data: {"content": "..."}
        - sources: 来源引用列表，data: {"sources": [...]}
        - done: 完成事件，data: {"conversation_id": "...", "message_id": "..."}
        - error: 错误事件，data: {"message": "..."}

    Example:
        >>> # JavaScript 前端调用示例
        >>> const eventSource = new EventSource('/api/chat/ask', {
        ...     method: 'POST',
        ...     body: JSON.stringify({question: "什么是 RAG？"})
        ... });
        >>> eventSource.onmessage = (e) => {
        ...     const {event, data} = JSON.parse(e.data);
        ...     console.log(event, data);
        ... };
    """
    logger.info(f"收到流式问答请求: question={request.question[:50]}..., conversation_id={request.conversation_id}")

    # 创建事件生成器（已直接通过 StreamingResponse 传递 rag_service.ask）

    # 返回 SSE 响应
    return StreamingResponse(
        _stream_rag_events(
            rag_service.ask(
                question=request.question,
                conversation_id=request.conversation_id,
                top_k=request.top_k,
                document_ids=request.document_ids,
            )
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@router.post("/ask/sync", response_model=ChatResponse)
async def chat_ask_sync(
    request: ChatRequest,
    rag_service: Any = Depends(get_rag_service_dependency),
) -> ChatResponse:
    """同步问答接口

    接收用户问题，返回完整的 AI 回答（非流式）。
    适用于不需要实时显示生成过程的场景。

    Args:
        request: 聊天请求数据，包含 question、conversation_id、top_k 等
        rag_service: RAG 服务实例（依赖注入）

    Returns:
        ChatResponse: 包含 answer、sources、conversation_id、message_id 的响应

    Raises:
        HTTPException: 当服务调用失败时返回 500 错误

    Example:
        >>> # Python 调用示例
        >>> import httpx
        >>> response = httpx.post(
        ...     "http://localhost:8000/api/chat/ask/sync",
        ...     json={"question": "什么是 RAG？"}
        ... )
        >>> result = response.json()
        >>> print(result["answer"])
    """
    logger.info(f"收到同步问答请求: question={request.question[:50]}..., conversation_id={request.conversation_id}")

    try:
        # 调用 RAG 服务的非流式问答方法
        result = await rag_service.ask_non_stream(
            question=request.question,
            conversation_id=request.conversation_id,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )

        logger.info(f"同步问答完成: conversation_id={result['conversation_id']}, message_id={result['message_id']}")

        # 构造响应
        return ChatResponse(
            conversation_id=result["conversation_id"],
            message_id=result["message_id"],
            answer=result["answer"],
            sources=result["sources"],
        )

    except Exception as e:
        logger.error(f"同步问答失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答服务异常: {str(e)}",
        ) from e


@router.post("/regenerate")
async def chat_regenerate(
    conversation_id: str,
    message_id: str | None = None,
    top_k: int | None = None,
    rag_service: Any = Depends(get_rag_service_dependency),
) -> StreamingResponse:
    """重新生成回答接口（SSE）

    基于对话历史重新生成最后一条回答。
    支持指定 message_id 重新生成特定消息。

    Args:
        conversation_id: 对话 ID（必填）
        message_id: 要重新生成的消息 ID（可选，默认最后一条）
        top_k: 检索文档数量（可选）
        rag_service: RAG 服务实例（依赖注入）

    Returns:
        EventSourceResponse: SSE 流式响应

    SSE 事件类型:
        - token: 生成的文本片段
        - sources: 来源引用列表
        - done: 完成事件
        - error: 错误事件

    Example:
        >>> # 重新生成最后一条回答
        >>> const eventSource = new EventSource(
        ...     '/api/chat/regenerate?conversation_id=conv-123'
        ... );
    """
    logger.info(f"收到重新生成请求: conversation_id={conversation_id}, message_id={message_id}")



    return StreamingResponse(
        _stream_rag_events(
            rag_service.regenerate(
                conversation_id=conversation_id,
                message_id=message_id,
                top_k=top_k,
            )
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
