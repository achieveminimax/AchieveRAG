"""
RAG 知识库助手 - 对话历史路由

提供对话创建、列表查询、详情获取、删除等 API 接口。
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.db.database import get_database
from backend.models.schemas import Conversation
from backend.services.conversation_service import (
    ConversationService,
    get_conversation_service,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/conversations", tags=["对话历史"])


class CreateConversationRequest(BaseModel):
    """创建对话请求体"""
    title: str | None = Field(None, max_length=100, description="对话标题，默认自动生成")


class UpdateConversationRequest(BaseModel):
    """更新对话请求体"""
    title: str = Field(..., min_length=1, max_length=100, description="新标题")


@router.post("", response_model=dict[str, Any])
async def create_conversation(request: CreateConversationRequest) -> dict[str, Any]:
    """创建新对话
    
    创建一个新的对话会话，可以指定标题，否则自动生成。
    
    Args:
        request: 创建对话请求
        
    Returns:
        创建的对话信息
    """
    service = get_conversation_service()
    
    try:
        conversation = service.create_conversation(title=request.title)
        
        return {
            "code": 200,
            "message": "success",
            "data": conversation,
        }
        
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建对话失败: {str(e)}")


@router.get("", response_model=dict[str, Any])
async def list_conversations() -> dict[str, Any]:
    """获取对话列表
    
    返回所有对话的列表，按更新时间倒序排列，包含每个对话的消息数量。
    
    Returns:
        对话列表
    """
    service = get_conversation_service()
    
    try:
        conversations = service.list_conversations()
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "conversations": conversations,
                "total": len(conversations),
            },
        }
        
    except Exception as e:
        logger.error(f"获取对话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取对话列表失败: {str(e)}")


@router.get("/{conversation_id}", response_model=dict[str, Any])
async def get_conversation_detail(conversation_id: str) -> dict[str, Any]:
    """获取对话详情
    
    获取指定对话的详细信息，包括所有消息。
    
    Args:
        conversation_id: 对话 ID
        
    Returns:
        对话详情（含消息列表）
        
    Raises:
        HTTPException: 对话不存在
    """
    service = get_conversation_service()
    
    try:
        result = service.get_conversation_detail(conversation_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return {
            "code": 200,
            "message": "success",
            "data": result,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取对话详情失败: {str(e)}")


@router.put("/{conversation_id}", response_model=dict[str, Any])
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
) -> dict[str, Any]:
    """更新对话标题
    
    更新指定对话的标题。
    
    Args:
        conversation_id: 对话 ID
        request: 更新请求
        
    Returns:
        更新后的对话信息
        
    Raises:
        HTTPException: 对话不存在
    """
    service = get_conversation_service()
    
    try:
        conversation = service.update_conversation_title(
            conversation_id=conversation_id,
            title=request.title,
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return {
            "code": 200,
            "message": "success",
            "data": conversation,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新对话失败: {str(e)}")


@router.delete("/{conversation_id}", response_model=dict[str, Any])
async def delete_conversation(conversation_id: str) -> dict[str, Any]:
    """删除对话
    
    删除指定对话及其所有消息。
    
    Args:
        conversation_id: 对话 ID
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 对话不存在
    """
    service = get_conversation_service()
    
    try:
        success = service.delete_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return {
            "code": 200,
            "message": "success",
            "data": None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除对话失败: {str(e)}")


@router.delete("", response_model=dict[str, Any])
async def delete_all_conversations() -> dict[str, Any]:
    """删除所有对话
    
    删除所有对话及其消息（危险操作）。
    
    Returns:
        删除结果
    """
    service = get_conversation_service()
    
    try:
        deleted_count = service.delete_all_conversations()
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "deleted_count": deleted_count,
            },
        }
        
    except Exception as e:
        logger.error(f"删除所有对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除所有对话失败: {str(e)}")
