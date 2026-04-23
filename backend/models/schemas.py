"""
RAG 知识库助手 - Pydantic 数据模型

定义所有 API 请求/响应的数据模型，用于自动校验和文档生成。
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class SourceReference(BaseModel):
    """来源引用数据模型
    
    表示回答中引用的文档来源信息。
    
    Attributes:
        source: 来源文件名
        page: 页码（可选）
        score: 相似度分数（0-1）
        text: 引用的文本片段（可选）
    """
    source: str = Field(..., description="来源文件名")
    document_id: Optional[str] = Field(None, description="来源文档 ID")
    page: Optional[int] = Field(None, description="页码")
    score: float = Field(..., ge=0.0, le=1.0, description="相似度分数")
    text: Optional[str] = Field(None, description="引用的文本片段")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "document.pdf",
                "document_id": "doc-uuid-123",
                "page": 5,
                "score": 0.89,
                "text": "RAG 是一种检索增强生成技术...",
            }
        }
    }


class ChatRequest(BaseModel):
    """聊天请求数据模型
    
    Attributes:
        question: 用户问题
        conversation_id: 对话 ID（可选，新对话可不传）
        top_k: 检索文档数量（可选，默认使用配置）
        stream: 是否使用流式输出（可选，默认 True）
    """
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    conversation_id: Optional[str] = Field(None, description="对话 ID，新对话可不传")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="检索文档数量")
    document_ids: list[str] = Field(default_factory=list, description="限定回答范围的文档 ID 列表")
    stream: bool = Field(True, description="是否使用流式输出")
    
    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """验证问题不为空"""
        if not v or not v.strip():
            raise ValueError("问题不能为空")
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "什么是 RAG 技术？",
                "conversation_id": None,
                "top_k": 5,
                "document_ids": ["doc-uuid-123"],
                "stream": True,
            }
        }
    }


class ChatResponse(BaseModel):
    """聊天响应数据模型（非流式）
    
    Attributes:
        conversation_id: 对话 ID
        message_id: 消息 ID
        answer: AI 回答内容
        sources: 来源引用列表
        created_at: 创建时间
    """
    conversation_id: str = Field(..., description="对话 ID")
    message_id: str = Field(..., description="消息 ID")
    answer: str = Field(..., description="AI 回答内容")
    sources: list[SourceReference] = Field(default=[], description="来源引用列表")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation_id": "conv-uuid-123",
                "message_id": "msg-uuid-456",
                "answer": "RAG（检索增强生成）是一种结合检索和生成的技术...",
                "sources": [
                    {
                        "source": "rag_intro.pdf",
                        "page": 1,
                        "score": 0.92,
                        "text": "RAG 是一种检索增强生成技术...",
                    }
                ],
                "created_at": "2024-01-15T10:30:00",
            }
        }
    }


class ChatStreamEvent(BaseModel):
    """聊天流式事件数据模型
    
    SSE 流中的事件数据结构。
    
    Attributes:
        event: 事件类型（token/sources/done/error）
        data: 事件数据
    """
    event: Literal["token", "sources", "done", "error"] = Field(..., description="事件类型")
    data: dict[str, Any] = Field(..., description="事件数据")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event": "token",
                    "data": {"content": "RAG 是"},
                },
                {
                    "event": "sources",
                    "data": {
                        "sources": [
                            {"source": "doc.pdf", "page": 1, "score": 0.89}
                        ]
                    },
                },
                {
                    "event": "done",
                    "data": {"conversation_id": "conv-123", "message_id": "msg-456"},
                },
                {
                    "event": "error",
                    "data": {"message": "检索失败"},
                },
            ]
        }
    }


class Message(BaseModel):
    """消息数据模型
    
    Attributes:
        id: 消息 ID
        conversation_id: 所属对话 ID
        role: 角色（user/assistant/system）
        content: 消息内容
        sources: 来源引用（仅 assistant 消息）
        created_at: 创建时间
    """
    id: str = Field(..., description="消息 ID")
    conversation_id: str = Field(..., description="所属对话 ID")
    role: Literal["user", "assistant", "system"] = Field(..., description="角色")
    content: str = Field(..., description="消息内容")
    sources: Optional[list[dict[str, Any]]] = Field(None, description="来源引用")
    created_at: str = Field(..., description="创建时间")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "msg-uuid-123",
                "conversation_id": "conv-uuid-456",
                "role": "assistant",
                "content": "RAG 是一种检索增强生成技术...",
                "sources": [
                    {"source": "doc.pdf", "page": 1, "score": 0.89}
                ],
                "created_at": "2024-01-15T10:30:00",
            }
        }
    }


class Conversation(BaseModel):
    """对话数据模型
    
    Attributes:
        id: 对话 ID
        title: 对话标题
        created_at: 创建时间
        updated_at: 更新时间
        message_count: 消息数量（可选）
    """
    id: str = Field(..., description="对话 ID")
    title: str = Field(..., description="对话标题")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    message_count: Optional[int] = Field(None, description="消息数量")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "conv-uuid-123",
                "title": "新对话 01-15 10:30",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:35:00",
                "message_count": 4,
            }
        }
    }


class DocumentInfo(BaseModel):
    """文档信息数据模型
    
    Attributes:
        id: 文档 ID
        filename: 文件名
        file_size: 文件大小（字节）
        file_type: 文件类型
        chunk_count: 分块数量
        status: 处理状态
        created_at: 创建时间
        updated_at: 更新时间
    """
    id: str = Field(..., description="文档 ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., ge=0, description="文件大小（字节）")
    file_type: str = Field(..., description="文件类型")
    chunk_count: int = Field(default=0, ge=0, description="分块数量")
    status: Literal["pending", "processing", "completed", "error"] = Field(
        ..., description="处理状态"
    )
    error_msg: Optional[str] = Field(None, description="错误信息")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    
    @property
    def file_size_human(self) -> str:
        """返回人类可读的文件大小"""
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "doc-uuid-123",
                "filename": "document.pdf",
                "file_size": 1024000,
                "file_type": "pdf",
                "chunk_count": 15,
                "status": "completed",
                "created_at": "2024-01-15T10:00:00",
                "updated_at": "2024-01-15T10:05:00",
            }
        }
    }


class DocumentUploadResponse(BaseModel):
    """文档上传响应数据模型
    
    Attributes:
        success: 是否上传成功
        document: 文档信息
        message: 提示信息
    """
    success: bool = Field(..., description="是否上传成功")
    document: Optional[DocumentInfo] = Field(None, description="文档信息")
    message: str = Field(..., description="提示信息")


class DocumentPreviewSection(BaseModel):
    """文档预览分段数据模型"""

    label: str = Field(..., description="分段标签")
    content: str = Field(..., description="分段内容")
    page: Optional[int] = Field(None, description="页码")
    heading: Optional[str] = Field(None, description="标题")
    section: Optional[int] = Field(None, description="节序号")
    paragraph: Optional[int] = Field(None, description="段落序号")
    table: Optional[int] = Field(None, description="表格序号")
    row: Optional[int] = Field(None, description="表格行号")


class DocumentPreviewResponse(BaseModel):
    """文档预览响应数据模型"""

    id: str = Field(..., description="文档 ID")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    sections: list[DocumentPreviewSection] = Field(default_factory=list, description="预览分段")
    truncated: bool = Field(False, description="是否已截断")


class SettingsResponse(BaseModel):
    """系统设置响应数据模型
    
    Attributes:
        llm_model: LLM 模型名称
        embedding_model: Embedding 模型名称
        default_top_k: 默认检索数量
        chunk_size: 文本分块大小
        chunk_overlap: 文本分块重叠大小
        max_chat_history: 最大对话历史轮数
    """
    llm_model: str = Field(..., description="LLM 模型名称")
    embedding_model: str = Field(..., description="Embedding 模型名称")
    default_top_k: int = Field(..., description="默认检索数量")
    chunk_size: int = Field(..., description="文本分块大小")
    chunk_overlap: int = Field(..., description="文本分块重叠大小")
    max_chat_history: int = Field(..., description="最大对话历史轮数")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "llm_model": "gpt-4o-mini",
                "embedding_model": "text-embedding-3-small",
                "default_top_k": 5,
                "chunk_size": 512,
                "chunk_overlap": 50,
                "max_chat_history": 10,
            }
        }
    }


class StatsResponse(BaseModel):
    """系统统计信息响应数据模型
    
    Attributes:
        total_documents: 文档总数
        total_chunks: 总分块数
        total_conversations: 对话总数
        total_messages: 消息总数
    """
    total_documents: int = Field(..., description="文档总数")
    total_chunks: int = Field(..., description="总分块数")
    total_conversations: int = Field(..., description="对话总数")
    total_messages: int = Field(..., description="消息总数")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_documents": 10,
                "total_chunks": 150,
                "total_conversations": 5,
                "total_messages": 25,
            }
        }
    }
