"""
RAG 知识库助手 - 系统设置路由

提供系统配置查询和更新 API 接口。
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from pydantic.fields import PydanticUndefined

from backend.config.settings import Settings, get_settings, reload_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["系统设置"])


class UpdateSettingsRequest(BaseModel):
    """更新设置请求体"""

    openai_api_key: str | None = Field(None, description="OpenAI API Key")
    openai_base_url: str | None = Field(None, description="OpenAI API Base URL")
    embedding_api_key: str | None = Field(None, description="Embedding API Key")
    embedding_base_url: str | None = Field(None, description="Embedding API Base URL")
    llm_model: str | None = Field(None, description="LLM 模型名称")
    embedding_model: str | None = Field(None, description="Embedding 模型名称")
    default_top_k: int | None = Field(None, ge=1, le=20, description="默认检索数量")
    chunk_size: int | None = Field(None, ge=100, le=2000, description="文本分块大小")
    chunk_overlap: int | None = Field(None, ge=0, le=500, description="文本分块重叠大小")
    max_chat_history: int | None = Field(None, ge=1, le=50, description="最大对话历史轮数")
    llm_temperature: float | None = Field(None, ge=0.0, le=2.0, description="LLM Temperature")
    llm_max_tokens: int | None = Field(None, ge=1, le=8192, description="LLM 最大生成 Token 数")
    similarity_threshold: float | None = Field(None, ge=0.0, le=1.0, description="相似度阈值")
    
    @field_validator("openai_api_key", "openai_base_url", "embedding_api_key", "embedding_base_url")
    @classmethod
    def normalize_optional_str(cls, v):
        """将空字符串视为 None"""
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v, info):
        """验证 chunk_overlap 不能超过 chunk_size"""
        if v is not None:
            chunk_size = info.data.get("chunk_size")
            if chunk_size is not None and v >= chunk_size:
                raise ValueError(f"chunk_overlap ({v}) 必须小于 chunk_size ({chunk_size})")
        return v


def _get_default_settings_payload() -> dict[str, Any]:
    """获取可重置的默认配置"""
    defaults: dict[str, Any] = {}
    keys = [
        "openai_base_url",
        "embedding_base_url",
        "llm_model",
        "embedding_model",
        "default_top_k",
        "chunk_size",
        "chunk_overlap",
        "max_chat_history",
        "llm_temperature",
        "llm_max_tokens",
        "similarity_threshold",
    ]

    for key in keys:
        field = Settings.model_fields.get(key)
        if field and field.default is not PydanticUndefined:
            defaults[key] = field.default

    return defaults


def _serialize_env_value(value: str) -> str:
    """序列化 .env 值，必要时添加引号"""
    if value == "":
        return '""'
    needs_quotes = any(char.isspace() for char in value) or any(char in value for char in ['#', '"'])
    if not needs_quotes:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _update_env_file(updates: dict[str, Any], env_path: Path) -> None:
    """更新 .env 文件配置"""
    lines: list[str | None] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    key_index: dict[str, int] = {}
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].strip()
        if "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key:
            key_index[key] = idx

    for key, value in updates.items():
        if value is None:
            if key in key_index:
                lines[key_index[key]] = None
            continue

        serialized = _serialize_env_value(str(value))
        new_line = f"{key}={serialized}"
        if key in key_index:
            lines[key_index[key]] = new_line
        else:
            lines.append(new_line)

    cleaned_lines = [line for line in lines if line is not None]
    env_path.write_text("\n".join(cleaned_lines) + "\n", encoding="utf-8")


@router.get("", response_model=dict[str, Any])
async def get_settings_info() -> dict[str, Any]:
    """获取当前配置
    
    返回当前系统的配置信息。
    
    Returns:
        配置信息
    """
    settings = get_settings()
    
    defaults = _get_default_settings_payload()

    return {
        "code": 200,
        "message": "success",
        "data": {
            "openai_base_url": settings.openai_base_url,
            "embedding_base_url": settings.embedding_base_url,
            "has_openai_api_key": bool(settings.openai_api_key),
            "has_embedding_api_key": bool(settings.embedding_api_key),
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "default_top_k": settings.default_top_k,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "max_chat_history": settings.max_chat_history,
            "llm_temperature": settings.llm_temperature,
            "llm_max_tokens": settings.llm_max_tokens,
            "similarity_threshold": settings.similarity_threshold,
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug": settings.debug,
            "data_dir": str(settings.data_dir),
            "upload_dir": str(settings.upload_dir),
            "chroma_persist_dir": str(settings.chroma_persist_dir),
            "db_path": str(settings.db_path),
            "defaults": defaults,
        },
    }


@router.put("", response_model=dict[str, Any])
async def update_settings(request: UpdateSettingsRequest) -> dict[str, Any]:
    """更新配置
    
    更新系统配置。注意：部分配置（如模型相关）需要重启服务才能生效。
    
    Args:
        request: 更新设置请求
        
    Returns:
        更新后的配置信息
        
    Raises:
        HTTPException: 配置更新失败
    """
    fields_set = request.model_fields_set
    current_settings = get_settings()
    defaults = _get_default_settings_payload()

    def get_default_value(key: str, fallback: Any) -> Any:
        return defaults.get(key, fallback)

    def set_update(field_name: str, env_key: str, value: Any) -> None:
        if field_name in fields_set:
            updates[env_key] = value

    updates: dict[str, Any] = {}

    if "openai_api_key" in fields_set:
        if request.openai_api_key is None:
            raise HTTPException(status_code=422, detail="OPENAI_API_KEY 不能为空")
        updates["OPENAI_API_KEY"] = request.openai_api_key

    set_update("openai_base_url", "OPENAI_BASE_URL", request.openai_base_url)
    set_update("embedding_api_key", "EMBEDDING_API_KEY", request.embedding_api_key)
    set_update("embedding_base_url", "EMBEDDING_BASE_URL", request.embedding_base_url)
    set_update("llm_model", "LLM_MODEL", request.llm_model)
    set_update("embedding_model", "EMBEDDING_MODEL", request.embedding_model)
    set_update("default_top_k", "DEFAULT_TOP_K", request.default_top_k)
    set_update("chunk_size", "CHUNK_SIZE", request.chunk_size)
    set_update("chunk_overlap", "CHUNK_OVERLAP", request.chunk_overlap)
    set_update("max_chat_history", "MAX_CHAT_HISTORY", request.max_chat_history)
    set_update("llm_temperature", "LLM_TEMPERATURE", request.llm_temperature)
    set_update("llm_max_tokens", "LLM_MAX_TOKENS", request.llm_max_tokens)
    set_update("similarity_threshold", "SIMILARITY_THRESHOLD", request.similarity_threshold)

    # 交叉字段校验：chunk_overlap 必须小于 chunk_size（考虑部分更新、重置为默认值的情况）
    chunk_size_effective = current_settings.chunk_size
    if "chunk_size" in fields_set:
        chunk_size_effective = (
            request.chunk_size
            if request.chunk_size is not None
            else get_default_value("chunk_size", current_settings.chunk_size)
        )

    if "chunk_overlap" in fields_set and request.chunk_overlap is not None:
        if request.chunk_overlap >= chunk_size_effective:
            raise HTTPException(
                status_code=422,
                detail=f"chunk_overlap ({request.chunk_overlap}) 必须小于 chunk_size ({chunk_size_effective})",
            )

    if "chunk_size" in fields_set:
        overlap_effective = current_settings.chunk_overlap
        if "chunk_overlap" in fields_set:
            overlap_effective = (
                request.chunk_overlap
                if request.chunk_overlap is not None
                else get_default_value("chunk_overlap", current_settings.chunk_overlap)
            )

        if chunk_size_effective is not None and overlap_effective is not None and overlap_effective >= chunk_size_effective:
            raise HTTPException(
                status_code=422,
                detail=f"chunk_overlap ({overlap_effective}) 必须小于 chunk_size ({chunk_size_effective})",
            )
    
    if not updates:
        return {
            "code": 200,
            "message": "没有要更新的配置",
            "data": None,
        }
    
    logger.info(f"配置更新请求: {updates}")

    env_path = Path(".env")
    try:
        _update_env_file(updates, env_path)
        settings = reload_settings()
    except Exception as exc:
        logger.error(f"更新配置失败: {exc}")
        raise HTTPException(status_code=500, detail="更新配置失败，请检查服务器日志") from exc

    # 返回更新后的配置
    return {
        "code": 200,
        "message": "配置已保存并生效",
        "data": {
            "openai_base_url": settings.openai_base_url,
            "embedding_base_url": settings.embedding_base_url,
            "has_openai_api_key": bool(settings.openai_api_key),
            "has_embedding_api_key": bool(settings.embedding_api_key),
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "default_top_k": settings.default_top_k,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "max_chat_history": settings.max_chat_history,
            "llm_temperature": settings.llm_temperature,
            "llm_max_tokens": settings.llm_max_tokens,
            "similarity_threshold": settings.similarity_threshold,
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug": settings.debug,
            "data_dir": str(settings.data_dir),
            "upload_dir": str(settings.upload_dir),
            "chroma_persist_dir": str(settings.chroma_persist_dir),
            "db_path": str(settings.db_path),
            "defaults": _get_default_settings_payload(),
        },
    }


@router.get("/models", response_model=dict[str, Any])
async def get_available_models() -> dict[str, Any]:
    """获取可用模型列表
    
    返回系统支持的 LLM 和 Embedding 模型列表。
    
    Returns:
        可用模型列表
    """
    from backend.core.embeddings import EmbeddingClient
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "llm_models": [
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "性价比高，推荐日常使用"},
                {"id": "gpt-4o", "name": "GPT-4o", "description": "更强的推理能力"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "速度快，成本低"},
            ],
            "embedding_models": [
                {"id": model, "name": model, "dimension": EmbeddingClient.get_model_dimension(model)}
                for model in EmbeddingClient.get_supported_models()
            ],
        },
    }


@router.get("/stats", response_model=dict[str, Any])
async def get_system_stats() -> dict[str, Any]:
    """获取系统统计信息
    
    返回系统整体的统计信息，包括文档、对话、消息等。
    
    Returns:
        系统统计信息
    """
    from backend.db.database import get_database
    
    db = get_database()
    settings = get_settings()
    
    # 获取文档统计
    doc_stats = db.get_document_stats()
    
    # 获取对话统计
    conversations = db.get_all_conversations()
    total_messages = 0
    for conv in conversations:
        messages = db.get_messages_by_conversation(conv["id"])
        total_messages += len(messages)
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "documents": {
                "total": doc_stats["total_documents"],
                "total_chunks": doc_stats["total_chunks"],
                "total_size": doc_stats["total_size"],
            },
            "conversations": {
                "total": len(conversations),
                "total_messages": total_messages,
            },
            "system": {
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "debug": settings.debug,
            },
        },
    }
