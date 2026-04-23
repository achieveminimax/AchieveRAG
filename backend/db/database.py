"""
RAG 知识库助手 - SQLite 数据库操作封装

提供文档、对话、消息等数据的持久化存储。
使用 SQLite 作为单机关系数据库，无需额外安装。
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from backend.config.settings import get_settings


class Database:
    """SQLite 数据库操作类
    
    封装所有数据库操作，包括：
    - 文档元数据管理（documents 表）
    - 对话记录管理（conversations 表）
    - 消息记录管理（messages 表）
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，默认从配置读取
        """
        if db_path is None:
            db_path = get_settings().db_path
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（懒加载）"""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection
    
    def close(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def init_tables(self):
        """初始化数据库表结构
        
        创建以下表：
        - documents: 文档元信息
        - conversations: 对话记录
        - messages: 消息记录
        """
        conn = self._get_connection()
        
        # documents 表 - 文档元信息
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id          TEXT PRIMARY KEY,
                filename    TEXT NOT NULL,
                file_path   TEXT NOT NULL,
                file_size   INTEGER,
                file_type   TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'pending',
                error_msg   TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # conversations 表 - 对话记录
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                title       TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # messages 表 - 消息记录
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role            TEXT NOT NULL,
                content         TEXT NOT NULL,
                sources         TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # 创建索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_status 
            ON documents(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_updated 
            ON conversations(updated_at DESC)
        """)
        
        conn.commit()
    
    def drop_tables(self):
        """删除所有表（危险操作，仅用于测试）"""
        conn = self._get_connection()
        conn.execute("DROP TABLE IF EXISTS messages")
        conn.execute("DROP TABLE IF EXISTS conversations")
        conn.execute("DROP TABLE IF EXISTS documents")
        conn.commit()
    
    # ==================== Document 操作 ====================
    
    def create_document(
        self,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: str,
        doc_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """创建文档记录
        
        Args:
            filename: 原始文件名
            file_path: 文件存储路径
            file_size: 文件大小（字节）
            file_type: 文件类型（pdf/md/txt/docx）
            doc_id: 文档 ID，默认自动生成 UUID
            
        Returns:
            创建的文档记录
        """
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO documents (id, filename, file_path, file_size, file_type, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (doc_id, filename, file_path, file_size, file_type),
        )
        conn.commit()
        
        return self.get_document(doc_id)
    
    def get_document(self, doc_id: str) -> Optional[dict[str, Any]]:
        """获取文档记录
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            文档记录，不存在返回 None
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM documents WHERE id = ?",
            (doc_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_documents(self) -> list[dict[str, Any]]:
        """获取所有文档记录
        
        Returns:
            文档记录列表，按创建时间倒序
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM documents ORDER BY created_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def update_document_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: Optional[int] = None,
        error_msg: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """更新文档状态
        
        Args:
            doc_id: 文档 ID
            status: 状态（pending/processing/completed/error）
            chunk_count: 分块数量
            error_msg: 错误信息
            
        Returns:
            更新后的文档记录
        """
        conn = self._get_connection()
        
        fields = ["status = ?", "updated_at = datetime('now')"]
        params = [status]
        
        if chunk_count is not None:
            fields.append("chunk_count = ?")
            params.append(chunk_count)
        
        if error_msg is not None:
            fields.append("error_msg = ?")
            params.append(error_msg)
        
        params.append(doc_id)
        
        conn.execute(
            f"UPDATE documents SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        conn.commit()
        
        return self.get_document(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档记录
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            是否删除成功
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    def get_document_stats(self) -> dict[str, Any]:
        """获取文档统计信息
        
        Returns:
            统计信息：文档总数、分块总数、总大小
        """
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_documents,
                COALESCE(SUM(chunk_count), 0) as total_chunks,
                COALESCE(SUM(file_size), 0) as total_size
            FROM documents
            WHERE status = 'completed'
        """)
        row = cursor.fetchone()
        return {
            "total_documents": row["total_documents"],
            "total_chunks": row["total_chunks"],
            "total_size": row["total_size"],
        }
    
    # ==================== Conversation 操作 ====================
    
    def create_conversation(self, title: Optional[str] = None) -> dict[str, Any]:
        """创建对话记录
        
        Args:
            title: 对话标题，默认自动生成
            
        Returns:
            创建的对话记录
        """
        conv_id = str(uuid.uuid4())
        
        if title is None:
            title = f"新对话 {datetime.now().strftime('%m-%d %H:%M')}"
        
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO conversations (id, title, created_at, updated_at)
            VALUES (?, ?, datetime('now'), datetime('now'))
            """,
            (conv_id, title),
        )
        conn.commit()
        
        return self.get_conversation(conv_id)
    
    def get_conversation(self, conv_id: str) -> Optional[dict[str, Any]]:
        """获取对话记录
        
        Args:
            conv_id: 对话 ID
            
        Returns:
            对话记录，不存在返回 None
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conv_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_conversations(self) -> list[dict[str, Any]]:
        """获取所有对话记录
        
        Returns:
            对话记录列表，按更新时间倒序
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all_conversations_with_message_count(self) -> list[dict[str, Any]]:
        """获取所有对话记录（包含消息数量）

        Returns:
            对话记录列表，按更新时间倒序；每条包含 message_count 字段
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT
                c.*,
                COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def update_conversation_title(self, conv_id: str, title: str) -> Optional[dict[str, Any]]:
        """更新对话标题
        
        Args:
            conv_id: 对话 ID
            title: 新标题
            
        Returns:
            更新后的对话记录
        """
        conn = self._get_connection()
        conn.execute(
            """
            UPDATE conversations 
            SET title = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (title, conv_id),
        )
        conn.commit()
        
        return self.get_conversation(conv_id)
    
    def update_conversation_timestamp(self, conv_id: str) -> Optional[dict[str, Any]]:
        """更新对话时间戳
        
        Args:
            conv_id: 对话 ID
            
        Returns:
            更新后的对话记录
        """
        conn = self._get_connection()
        conn.execute(
            """
            UPDATE conversations 
            SET updated_at = datetime('now')
            WHERE id = ?
            """,
            (conv_id,),
        )
        conn.commit()
        
        return self.get_conversation(conv_id)
    
    def delete_conversation(self, conv_id: str) -> bool:
        """删除对话记录（级联删除消息）
        
        Args:
            conv_id: 对话 ID
            
        Returns:
            是否删除成功
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    # ==================== Message 操作 ====================
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """添加消息记录
        
        Args:
            conversation_id: 所属对话 ID
            role: 角色（user/assistant/system）
            content: 消息内容
            sources: 来源引用（仅 assistant 消息）
            
        Returns:
            创建的消息记录
        """
        msg_id = str(uuid.uuid4())
        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
        
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, sources)
            VALUES (?, ?, ?, ?, ?)
            """,
            (msg_id, conversation_id, role, content, sources_json),
        )
        conn.commit()
        
        # 更新对话时间戳
        self.update_conversation_timestamp(conversation_id)
        
        return self.get_message(msg_id)
    
    def get_message(self, msg_id: str) -> Optional[dict[str, Any]]:
        """获取消息记录
        
        Args:
            msg_id: 消息 ID
            
        Returns:
            消息记录，不存在返回 None
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM messages WHERE id = ?",
            (msg_id,),
        )
        row = cursor.fetchone()
        
        if row:
            result = dict(row)
            if result.get("sources"):
                result["sources"] = json.loads(result["sources"])
            return result
        return None
    
    def get_messages_by_conversation(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """获取对话的所有消息
        
        Args:
            conversation_id: 对话 ID
            limit: 限制返回数量，默认返回全部
            
        Returns:
            消息记录列表，按时间正序
        """
        conn = self._get_connection()
        
        sql = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC"
        params = [conversation_id]
        
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        
        cursor = conn.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            if result.get("sources"):
                result["sources"] = json.loads(result["sources"])
            results.append(result)
        
        return results
    
    def get_recent_messages(
        self,
        conversation_id: str,
        n: int = 10,
    ) -> list[dict[str, Any]]:
        """获取最近的 N 条消息
        
        Args:
            conversation_id: 对话 ID
            n: 消息数量
            
        Returns:
            消息记录列表，按时间正序
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (conversation_id, n),
        )
        
        rows = cursor.fetchall()
        rows.reverse()  # 转为正序
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get("sources"):
                result["sources"] = json.loads(result["sources"])
            results.append(result)
        
        return results
    
    def delete_message(self, msg_id: str) -> bool:
        """删除消息记录
        
        Args:
            msg_id: 消息 ID
            
        Returns:
            是否删除成功
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        conn.commit()
        return cursor.rowcount > 0


# 全局数据库实例（单例模式）
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """获取数据库实例（单例模式）
    
    Returns:
        Database 实例
        
    Example:
        >>> from backend.db.database import get_database
        >>> db = get_database()
        >>> db.init_tables()
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def init_database(db_path: Optional[Path] = None) -> Database:
    """初始化数据库（创建表结构）
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        初始化后的 Database 实例
        
    Example:
        >>> from backend.db.database import init_database
        >>> db = init_database()
        >>> print("数据库初始化完成")
    """
    db = Database(db_path)
    db.init_tables()
    return db
