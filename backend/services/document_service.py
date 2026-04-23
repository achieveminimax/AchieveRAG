"""
RAG 知识库助手 - 文档处理服务

提供文档上传处理逻辑，包括：
- 文件保存
- 文档解析
- 文本分块
- 向量化
- 向量库存储
- 状态更新
"""

import asyncio
import shutil
from pathlib import Path
from typing import Any, Optional

from backend.config.settings import Settings, get_settings
from backend.core.document_loader import DocumentLoader
from backend.core.embeddings import EmbeddingClient, get_embedding_client
from backend.core.text_splitter import TextSplitter, get_text_splitter_from_settings
from backend.core.vectorstore import VectorStore, get_vectorstore
from backend.db.database import Database, get_database
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentService:
    """文档处理服务类
    
    封装文档上传和处理的完整流程，包括文件保存、解析、分块、向量化和存储。
    
    Attributes:
        db: 数据库实例
        settings: 应用配置
        document_loader: 文档加载器
        text_splitter: 文本分块器
        embedding_client: Embedding 客户端
        vectorstore: 向量存储实例
    
    Example:
        >>> from backend.services.document_service import DocumentService
        >>> service = DocumentService()
        >>> result = await service.process_upload(
        ...     filename="document.pdf",
        ...     content=b"...",
        ...     content_type="application/pdf",
        ... )
    """
    
    def __init__(
        self,
        db: Optional[Database] = None,
        settings: Optional[Settings] = None,
        document_loader: Optional[DocumentLoader] = None,
        text_splitter: Optional[TextSplitter] = None,
        embedding_client: Optional[EmbeddingClient] = None,
        vectorstore: Optional[VectorStore] = None,
    ):
        """初始化文档处理服务
        
        Args:
            db: 数据库实例，默认使用全局实例
            settings: 应用配置，默认自动加载
            document_loader: 文档加载器，默认创建新实例
            text_splitter: 文本分块器，默认根据配置创建
            embedding_client: Embedding 客户端，默认使用全局实例
            vectorstore: 向量存储实例，默认使用全局实例
        """
        self._settings = settings or get_settings()
        self._db = db or get_database()
        self._document_loader = document_loader or DocumentLoader()
        self._text_splitter = text_splitter or get_text_splitter_from_settings()
        self._embedding_client = embedding_client or get_embedding_client()
        self._vectorstore = vectorstore or get_vectorstore(
            embedding_client=self._embedding_client,
            settings=self._settings,
        )
    
    async def process_upload(
        self,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """处理文档上传
        
        完整的文档处理流程：
        1. 保存文件到本地
        2. 创建数据库记录
        3. 解析文档
        4. 文本分块
        5. 向量化
        6. 存储到向量库
        7. 更新数据库状态
        
        Args:
            filename: 原始文件名
            content: 文件内容（字节）
            content_type: MIME 类型
            
        Returns:
            处理结果字典，包含：
            - success: 是否成功
            - document: 文档信息（成功时）
            - message: 提示信息
        """
        doc_record = None
        file_path = None
        
        try:
            # 1. 保存文件到本地
            file_path = await asyncio.to_thread(self._save_file, filename, content)
            logger.info(f"文件已保存: {file_path}")
            
            # 2. 创建数据库记录
            file_size = len(content)
            file_type = Path(filename).suffix.lower().lstrip(".")
            
            doc_record = self._db.create_document(
                filename=filename,
                file_path=str(file_path),
                file_size=file_size,
                file_type=file_type,
            )
            logger.info(f"文档记录已创建: {doc_record['id']}")
            
            # 3. 更新状态为处理中
            self._db.update_document_status(
                doc_id=doc_record["id"],
                status="processing",
            )
            
            # 4. 解析文档
            try:
                documents = await asyncio.to_thread(self._document_loader.load, file_path)
                logger.info(f"文档解析完成: {len(documents)} 个片段")
            except Exception as e:
                logger.error(f"文档解析失败: {e}")
                self._db.update_document_status(
                    doc_id=doc_record["id"],
                    status="error",
                    error_msg=f"解析失败: {str(e)}",
                )
                return {
                    "success": False,
                    "message": f"文档解析失败: {str(e)}",
                }
            
            # 5. 文本分块
            try:
                chunks = await asyncio.to_thread(self._text_splitter.split_documents, documents)
                logger.info(f"文本分块完成: {len(chunks)} 个块")
            except Exception as e:
                logger.error(f"文本分块失败: {e}")
                self._db.update_document_status(
                    doc_id=doc_record["id"],
                    status="error",
                    error_msg=f"分块失败: {str(e)}",
                )
                return {
                    "success": False,
                    "message": f"文本分块失败: {str(e)}",
                }
            
            # 6. 向量化并存储到向量库
            try:
                await self._store_chunks(doc_record["id"], filename, chunks)
                logger.info(f"向量存储完成: {len(chunks)} 个块")
            except Exception as e:
                logger.error(f"向量存储失败: {e}")
                self._db.update_document_status(
                    doc_id=doc_record["id"],
                    status="error",
                    error_msg=f"向量化失败: {str(e)}",
                )
                return {
                    "success": False,
                    "message": f"向量化失败: {str(e)}",
                }
            
            # 7. 更新数据库状态为完成
            self._db.update_document_status(
                doc_id=doc_record["id"],
                status="completed",
                chunk_count=len(chunks),
            )
            
            logger.info(f"文档处理完成: {doc_record['id']}")
            
            return {
                "success": True,
                "document": {
                    "id": doc_record["id"],
                    "filename": doc_record["filename"],
                    "file_size": doc_record["file_size"],
                    "file_type": doc_record["file_type"],
                    "chunk_count": len(chunks),
                    "status": "completed",
                    "created_at": doc_record["created_at"],
                },
                "message": f"文档上传成功，共处理 {len(chunks)} 个文本块",
            }
            
        except Exception as e:
            logger.error(f"文档处理失败: {e}")
            
            # 更新数据库状态为错误
            if doc_record:
                self._db.update_document_status(
                    doc_id=doc_record["id"],
                    status="error",
                    error_msg=str(e),
                )
            
            # 清理已保存的文件
            if file_path and file_path.exists():
                file_path.unlink()
            
            return {
                "success": False,
                "message": f"处理失败: {str(e)}",
            }

    async def process_upload_file(
        self,
        filename: str,
        file_obj: Any,
        content_type: str,
        file_size: int,
    ) -> dict[str, Any]:
        doc_record = None
        file_path = None

        try:
            file_path = await asyncio.to_thread(self._save_fileobj, filename, file_obj)
            logger.info(f"文件已保存: {file_path}")

            file_type = Path(filename).suffix.lower().lstrip(".")

            doc_record = self._db.create_document(
                filename=filename,
                file_path=str(file_path),
                file_size=file_size,
                file_type=file_type,
            )
            logger.info(f"文档记录已创建: {doc_record['id']}")

            self._db.update_document_status(
                doc_id=doc_record["id"],
                status="processing",
            )

            try:
                documents = await asyncio.to_thread(self._document_loader.load, file_path)
                logger.info(f"文档解析完成: {len(documents)} 个片段")
            except Exception as e:
                logger.error(f"文档解析失败: {e}")
                self._db.update_document_status(
                    doc_id=doc_record["id"],
                    status="error",
                    error_msg=f"解析失败: {str(e)}",
                )
                return {
                    "success": False,
                    "message": f"文档解析失败: {str(e)}",
                }

            try:
                chunks = await asyncio.to_thread(self._text_splitter.split_documents, documents)
                logger.info(f"文本分块完成: {len(chunks)} 个块")
            except Exception as e:
                logger.error(f"文本分块失败: {e}")
                self._db.update_document_status(
                    doc_id=doc_record["id"],
                    status="error",
                    error_msg=f"分块失败: {str(e)}",
                )
                return {
                    "success": False,
                    "message": f"文本分块失败: {str(e)}",
                }

            try:
                await self._store_chunks(doc_record["id"], filename, chunks)
                logger.info(f"向量存储完成: {len(chunks)} 个块")
            except Exception as e:
                logger.error(f"向量存储失败: {e}")
                self._db.update_document_status(
                    doc_id=doc_record["id"],
                    status="error",
                    error_msg=f"向量化失败: {str(e)}",
                )
                return {
                    "success": False,
                    "message": f"向量化失败: {str(e)}",
                }

            self._db.update_document_status(
                doc_id=doc_record["id"],
                status="completed",
                chunk_count=len(chunks),
            )

            logger.info(f"文档处理完成: {doc_record['id']}")

            return {
                "success": True,
                "document": {
                    "id": doc_record["id"],
                    "filename": doc_record["filename"],
                    "file_size": doc_record["file_size"],
                    "file_type": doc_record["file_type"],
                    "chunk_count": len(chunks),
                    "status": "completed",
                    "created_at": doc_record["created_at"],
                },
                "message": f"文档上传成功，共处理 {len(chunks)} 个文本块",
            }

        except Exception as e:
            logger.error(f"文档处理失败: {e}")

            if doc_record:
                self._db.update_document_status(
                    doc_id=doc_record["id"],
                    status="error",
                    error_msg=str(e),
                )

            if file_path and file_path.exists():
                file_path.unlink()

            return {
                "success": False,
                "message": f"处理失败: {str(e)}",
            }
    
    def _save_file(self, filename: str, content: bytes) -> Path:
        """保存文件到上传目录
        
        Args:
            filename: 原始文件名
            content: 文件内容
            
        Returns:
            保存后的文件路径
        """
        # 确保上传目录存在
        upload_dir = self._settings.upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一文件名（避免冲突）
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{unique_id}_{filename}"
        file_path = upload_dir / safe_filename
        
        # 写入文件
        file_path.write_bytes(content)
        
        return file_path

    def _save_fileobj(self, filename: str, file_obj: Any) -> Path:
        upload_dir = self._settings.upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)

        import uuid

        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{unique_id}_{filename}"
        file_path = upload_dir / safe_filename

        try:
            file_obj.seek(0)
        except Exception:
            pass

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)

        return file_path
    
    async def _store_chunks(
        self,
        document_id: str,
        source: str,
        chunks: list,
    ) -> list[str]:
        """存储文本块到向量库
        
        Args:
            document_id: 文档 ID
            source: 来源文件名
            chunks: 文本块列表（Document 对象）
            
        Returns:
            存储的文档 ID 列表
        """
        if not chunks:
            return []
        
        # 准备文档数据
        documents = []
        for i, chunk in enumerate(chunks):
            # 构建元数据
            metadata = chunk.metadata.copy()
            metadata["document_id"] = document_id
            metadata["chunk_index"] = i
            
            documents.append({
                "text": chunk.page_content,
                "metadata": metadata,
            })
        
        # 批量添加到向量库
        ids = await self._vectorstore.add_documents(documents)
        
        return ids
    
    async def delete_document_vectors(self, document_id: str) -> int:
        """删除文档的向量
        
        删除向量库中所有关联到指定文档 ID 的向量。
        
        Args:
            document_id: 文档 ID
            
        Returns:
            删除的向量数量
        """
        try:
            deleted_count = self._vectorstore.delete_by_document_id(document_id)
            logger.info(f"已删除文档 {document_id} 的 {deleted_count} 个向量")
            return deleted_count
        except Exception as e:
            logger.error(f"删除文档向量失败: {e}")
            raise
    
    async def reprocess_document(self, document_id: str) -> dict[str, Any]:
        """重新处理文档
        
        删除旧向量并重新解析、分块、向量化文档。
        
        Args:
            document_id: 文档 ID
            
        Returns:
            处理结果
        """
        # 获取文档记录
        doc_record = self._db.get_document(document_id)
        if not doc_record:
            return {
                "success": False,
                "message": "文档不存在",
            }
        
        file_path = Path(doc_record["file_path"])
        if not file_path.exists():
            return {
                "success": False,
                "message": "文件不存在",
            }
        
        try:
            # 删除旧向量
            await self.delete_document_vectors(document_id)
            
            # 更新状态为处理中
            self._db.update_document_status(
                doc_id=document_id,
                status="processing",
                chunk_count=0,
            )
            
            # 重新解析文档
            documents = self._document_loader.load(file_path)
            
            # 重新分块
            chunks = self._text_splitter.split_documents(documents)
            
            # 重新向量化并存储
            await self._store_chunks(document_id, doc_record["filename"], chunks)
            
            # 更新状态为完成
            self._db.update_document_status(
                doc_id=document_id,
                status="completed",
                chunk_count=len(chunks),
            )
            
            return {
                "success": True,
                "message": f"重新处理完成，共 {len(chunks)} 个块",
                "chunk_count": len(chunks),
            }
            
        except Exception as e:
            logger.error(f"重新处理文档失败: {e}")
            self._db.update_document_status(
                doc_id=document_id,
                status="error",
                error_msg=str(e),
            )
            return {
                "success": False,
                "message": f"重新处理失败: {str(e)}",
            }


# 全局 DocumentService 实例（单例模式）
_document_service_instance: Optional[DocumentService] = None


def get_document_service(
    db: Optional[Database] = None,
    settings: Optional[Settings] = None,
    document_loader: Optional[DocumentLoader] = None,
    text_splitter: Optional[TextSplitter] = None,
    embedding_client: Optional[EmbeddingClient] = None,
    vectorstore: Optional[VectorStore] = None,
) -> DocumentService:
    """获取 DocumentService 实例（单例模式）
    
    使用单例模式避免重复创建服务实例，提高性能。
    
    Args:
        db: 数据库实例
        settings: 应用配置
        document_loader: 文档加载器
        text_splitter: 文本分块器
        embedding_client: Embedding 客户端
        vectorstore: 向量存储实例
        
    Returns:
        DocumentService 实例
        
    Example:
        >>> from backend.services.document_service import get_document_service
        >>> service = get_document_service()
        >>> result = await service.process_upload(filename, content, content_type)
    """
    global _document_service_instance
    if _document_service_instance is None:
        _document_service_instance = DocumentService(
            db=db,
            settings=settings,
            document_loader=document_loader,
            text_splitter=text_splitter,
            embedding_client=embedding_client,
            vectorstore=vectorstore,
        )
    return _document_service_instance


def reset_document_service() -> None:
    """重置全局 DocumentService 实例
    
    用于测试或需要重新初始化服务的场景。
    """
    global _document_service_instance
    _document_service_instance = None
