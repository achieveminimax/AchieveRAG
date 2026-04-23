"""
RAG 知识库助手 - 文档管理路由

提供文档上传、列表查询、删除、统计等 API 接口。
"""

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config.settings import get_settings
from backend.core.document_loader import DocumentLoader
from backend.db.database import get_database
from backend.models.schemas import DocumentInfo, DocumentPreviewResponse, DocumentUploadResponse
from backend.services.document_service import DocumentService, get_document_service
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["文档管理"])
MAX_PREVIEW_CHARS = 200_000


@router.post("/upload", response_model=dict[str, Any])
async def upload_documents(
    files: list[UploadFile] = File(..., description="要上传的文档文件，支持多文件"),
) -> dict[str, Any]:
    """上传文档
    
    支持多文件同时上传，支持的格式：PDF、Markdown、TXT、DOCX。
    上传后会自动解析、分块、向量化并存储到向量库。
    
    Args:
        files: 文件列表
        
    Returns:
        上传结果，包含成功和失败的文件列表
        
    Raises:
        HTTPException: 文件格式不支持或上传失败
    """
    settings = get_settings()
    service = get_document_service()
    
    results = {
        "code": 200,
        "message": "success",
        "data": {
            "success": [],
            "failed": [],
        },
    }
    
    for file in files:
        try:
            # 验证文件类型
            if not settings.is_allowed_file(file.filename):
                results["data"]["failed"].append({
                    "filename": file.filename,
                    "error": f"不支持的文件类型。支持的类型: {', '.join(settings.allowed_extensions_list)}",
                })
                continue
            
            # 验证文件大小
            try:
                file.file.seek(0, 2)
                file_size = file.file.tell()
                file.file.seek(0)
            except Exception:
                file_size = None

            if file_size is not None and file_size > settings.max_file_size:
                results["data"]["failed"].append({
                    "filename": file.filename,
                    "error": f"文件大小超过限制（最大 {settings.max_file_size_mb}MB）",
                })
                continue
            
            # 处理上传
            if file_size is None:
                content = await file.read()
                if len(content) > settings.max_file_size:
                    results["data"]["failed"].append({
                        "filename": file.filename,
                        "error": f"文件大小超过限制（最大 {settings.max_file_size_mb}MB）",
                    })
                    continue

                result = await service.process_upload(
                    filename=file.filename,
                    content=content,
                    content_type=file.content_type or "application/octet-stream",
                )
            else:
                result = await service.process_upload_file(
                    filename=file.filename,
                    file_obj=file.file,
                    content_type=file.content_type or "application/octet-stream",
                    file_size=file_size,
                )
            
            if result["success"]:
                results["data"]["success"].append(result)
            else:
                results["data"]["failed"].append({
                    "filename": file.filename,
                    "error": result.get("message", "处理失败"),
                })
                
        except Exception as e:
            logger.error(f"上传文件 {file.filename} 失败: {e}")
            results["data"]["failed"].append({
                "filename": file.filename,
                "error": str(e),
            })
        finally:
            await file.close()
    
    # 如果有失败的文件，调整返回状态
    if not results["data"]["success"] and results["data"]["failed"]:
        results["code"] = 400
        results["message"] = "所有文件上传失败"
    elif results["data"]["failed"]:
        results["message"] = "部分文件上传失败"
    
    return results


@router.get("", response_model=dict[str, Any])
async def list_documents() -> dict[str, Any]:
    """获取文档列表
    
    返回所有已上传文档的列表，按创建时间倒序排列。
    
    Returns:
        文档列表
    """
    db = get_database()
    documents = db.get_all_documents()
    
    # 转换为响应模型
    document_list = []
    for doc in documents:
        document_list.append(DocumentInfo(
            id=doc["id"],
            filename=doc["filename"],
            file_size=doc["file_size"],
            file_type=doc["file_type"],
            chunk_count=doc.get("chunk_count", 0),
            status=doc["status"],
            error_msg=doc.get("error_msg"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        ))
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "documents": [doc.model_dump() for doc in document_list],
            "total": len(document_list),
        },
    }


@router.delete("/{doc_id}", response_model=dict[str, Any])
async def delete_document(doc_id: str) -> dict[str, Any]:
    """删除文档
    
    删除指定文档及其在向量库中的所有分块。
    
    Args:
        doc_id: 文档 ID
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 文档不存在
    """
    db = get_database()
    service = get_document_service()
    
    # 检查文档是否存在
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    try:
        # 删除向量库中的文档
        deleted_chunks = await service.delete_document_vectors(doc_id)
        
        # 删除物理文件
        file_path = Path(document["file_path"])
        if file_path.exists():
            file_path.unlink()
        
        # 删除数据库记录
        db.delete_document(doc_id)
        
        logger.info(f"文档 {doc_id} 已删除，共删除 {deleted_chunks} 个向量分块")
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "deleted_chunks": deleted_chunks,
            },
        }
        
    except Exception as e:
        logger.error(f"删除文档 {doc_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/stats", response_model=dict[str, Any])
async def get_document_stats() -> dict[str, Any]:
    """获取知识库统计信息
    
    返回知识库的统计信息，包括：
    - 文档总数
    - 分块总数
    - 总大小（字节）
    
    Returns:
        统计信息
    """
    db = get_database()
    stats = db.get_document_stats()
    
    # 计算人类可读的大小
    total_size = stats["total_size"]
    size_str = _format_file_size(total_size)
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "total_documents": stats["total_documents"],
            "total_chunks": stats["total_chunks"],
            "total_size": total_size,
            "total_size_human": size_str,
        },
    }


@router.get("/{doc_id}/content", response_model=dict[str, Any])
async def get_document_content(doc_id: str) -> dict[str, Any]:
    """获取文档预览内容

    解析已上传文档，返回适合前端展示的文本分段内容。
    预览内容会在过长时自动截断，避免响应过大。
    """
    db = get_database()
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = Path(document["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文档文件不存在")

    try:
        loader = DocumentLoader()
        parsed_docs = loader.load(file_path)

        preview_sections: list[dict[str, str]] = []
        current_length = 0
        truncated = False

        for index, parsed_doc in enumerate(parsed_docs, start=1):
            label = _get_preview_section_label(parsed_doc.metadata, index)
            content = parsed_doc.page_content.strip()
            if not content:
                continue

            remaining = MAX_PREVIEW_CHARS - current_length
            if remaining <= 0:
                truncated = True
                break

            if len(content) > remaining:
                content = content[:remaining].rstrip() + "\n\n[预览内容已截断]"
                truncated = True

            preview_sections.append({
                "label": label,
                "content": content,
                "page": parsed_doc.metadata.get("page"),
                "heading": parsed_doc.metadata.get("heading"),
                "section": parsed_doc.metadata.get("section"),
                "paragraph": parsed_doc.metadata.get("paragraph"),
                "table": parsed_doc.metadata.get("table"),
                "row": parsed_doc.metadata.get("row"),
            })
            current_length += len(content)

            if truncated:
                break

        preview = DocumentPreviewResponse(
            id=document["id"],
            filename=document["filename"],
            file_type=document["file_type"],
            sections=preview_sections,
            truncated=truncated,
        )

        return {
            "code": 200,
            "message": "success",
            "data": preview.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档预览失败 {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档内容失败: {str(e)}")


@router.get("/{doc_id}", response_model=dict[str, Any])
async def get_document_detail(doc_id: str) -> dict[str, Any]:
    """获取文档详情
    
    返回指定文档的详细信息。
    
    Args:
        doc_id: 文档 ID
        
    Returns:
        文档详情
        
    Raises:
        HTTPException: 文档不存在
    """
    db = get_database()
    
    document = db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    doc_info = DocumentInfo(
        id=document["id"],
        filename=document["filename"],
        file_size=document["file_size"],
        file_type=document["file_type"],
        chunk_count=document.get("chunk_count", 0),
        status=document["status"],
        error_msg=document.get("error_msg"),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )
    
    return {
        "code": 200,
        "message": "success",
        "data": doc_info.model_dump(),
    }


def _format_file_size(size_bytes: int) -> str:
    """格式化文件大小为人类可读格式
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化后的字符串，如 "1.5 MB"
    """
    if size_bytes == 0:
        return "0 B"
    
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    
    return f"{size_bytes:.1f} TB"


def _get_preview_section_label(metadata: dict[str, Any], index: int) -> str:
    """根据文档元数据生成预览分段标签"""
    if metadata.get("page"):
        return f"第 {metadata['page']} 页"

    heading = metadata.get("heading")
    if heading:
        return str(heading)

    if metadata.get("section") is not None:
        return f"第 {int(metadata['section']) + 1} 节"

    if metadata.get("paragraph"):
        return f"第 {metadata['paragraph']} 段"

    if metadata.get("table") and metadata.get("row"):
        return f"表格 {metadata['table']} - 第 {metadata['row']} 行"

    return f"第 {index} 段"
