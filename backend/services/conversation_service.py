"""
RAG 知识库助手 - 对话管理服务

提供对话管理功能，包括：
- 创建对话
- 查询对话列表
- 查询对话详情（含消息）
- 更新对话标题
- 删除对话
"""

from typing import Any, Optional

from backend.config.settings import Settings, get_settings
from backend.db.database import Database, get_database
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationService:
    """对话管理服务类
    
    封装对话的增删改查操作，提供高层次的对话管理接口。
    
    Attributes:
        db: 数据库实例
        settings: 应用配置
    
    Example:
        >>> from backend.services.conversation_service import ConversationService
        >>> service = ConversationService()
        >>> conversation = service.create_conversation(title="新对话")
        >>> conversations = service.list_conversations()
    """
    
    def __init__(
        self,
        db: Optional[Database] = None,
        settings: Optional[Settings] = None,
    ):
        """初始化对话管理服务
        
        Args:
            db: 数据库实例，默认使用全局实例
            settings: 应用配置，默认自动加载
        """
        self._settings = settings or get_settings()
        self._db = db or get_database()
    
    def create_conversation(self, title: Optional[str] = None) -> dict[str, Any]:
        """创建新对话
        
        创建一个新的对话会话，可以指定标题，否则自动生成。
        
        Args:
            title: 对话标题，默认自动生成（格式：新对话 MM-DD HH:MM）
            
        Returns:
            创建的对话记录，包含：
            - id: 对话 ID
            - title: 对话标题
            - created_at: 创建时间
            - updated_at: 更新时间
            
        Example:
            >>> conversation = service.create_conversation(title="关于 RAG 的讨论")
            >>> print(conversation["id"])
        """
        try:
            conversation = self._db.create_conversation(title=title)
            logger.info(f"对话已创建: {conversation['id']}")
            return conversation
        except Exception as e:
            logger.error(f"创建对话失败: {e}")
            raise
    
    def list_conversations(self) -> list[dict[str, Any]]:
        """获取对话列表
        
        返回所有对话的列表，按更新时间倒序排列，包含每个对话的消息数量。
        
        Returns:
            对话列表，每个对话包含：
            - id: 对话 ID
            - title: 对话标题
            - created_at: 创建时间
            - updated_at: 更新时间
            - message_count: 消息数量
            
        Example:
            >>> conversations = service.list_conversations()
            >>> for conv in conversations:
            ...     print(f"{conv['title']}: {conv['message_count']} 条消息")
        """
        try:
            return self._db.get_all_conversations_with_message_count()
        except Exception as e:
            logger.error(f"获取对话列表失败: {e}")
            raise
    
    def get_conversation(self, conversation_id: str) -> Optional[dict[str, Any]]:
        """获取对话信息
        
        获取指定对话的基本信息（不含消息）。
        
        Args:
            conversation_id: 对话 ID
            
        Returns:
            对话记录，不存在返回 None
            
        Example:
            >>> conversation = service.get_conversation("conv-uuid-123")
            >>> if conversation:
            ...     print(conversation["title"])
        """
        try:
            return self._db.get_conversation(conversation_id)
        except Exception as e:
            logger.error(f"获取对话失败: {e}")
            raise
    
    def get_conversation_detail(self, conversation_id: str) -> Optional[dict[str, Any]]:
        """获取对话详情
        
        获取指定对话的详细信息，包括所有消息。
        
        Args:
            conversation_id: 对话 ID
            
        Returns:
            对话详情，包含：
            - id: 对话 ID
            - title: 对话标题
            - created_at: 创建时间
            - updated_at: 更新时间
            - message_count: 消息数量
            - messages: 消息列表
            
            对话不存在返回 None
            
        Example:
            >>> detail = service.get_conversation_detail("conv-uuid-123")
            >>> if detail:
            ...     print(f"共 {detail['message_count']} 条消息")
            ...     for msg in detail["messages"]:
            ...         print(f"{msg['role']}: {msg['content'][:50]}...")
        """
        try:
            # 获取对话基本信息
            conversation = self._db.get_conversation(conversation_id)
            if not conversation:
                return None
            
            # 获取消息列表
            messages = self._db.get_messages_by_conversation(conversation_id)
            
            # 组装详情
            detail = {
                **conversation,
                "message_count": len(messages),
                "messages": messages,
            }
            
            return detail
        except Exception as e:
            logger.error(f"获取对话详情失败: {e}")
            raise
    
    def update_conversation_title(
        self,
        conversation_id: str,
        title: str,
    ) -> Optional[dict[str, Any]]:
        """更新对话标题
        
        更新指定对话的标题。
        
        Args:
            conversation_id: 对话 ID
            title: 新标题
            
        Returns:
            更新后的对话记录，对话不存在返回 None
            
        Example:
            >>> conversation = service.update_conversation_title(
            ...     "conv-uuid-123",
            ...     "新的标题"
            ... )
        """
        try:
            conversation = self._db.update_conversation_title(conversation_id, title)
            if conversation:
                logger.info(f"对话标题已更新: {conversation_id} -> {title}")
            return conversation
        except Exception as e:
            logger.error(f"更新对话标题失败: {e}")
            raise
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话
        
        删除指定对话及其所有消息（级联删除）。
        
        Args:
            conversation_id: 对话 ID
            
        Returns:
            是否删除成功
            
        Example:
            >>> if service.delete_conversation("conv-uuid-123"):
            ...     print("删除成功")
        """
        try:
            success = self._db.delete_conversation(conversation_id)
            if success:
                logger.info(f"对话已删除: {conversation_id}")
            return success
        except Exception as e:
            logger.error(f"删除对话失败: {e}")
            raise
    
    def delete_all_conversations(self) -> int:
        """删除所有对话
        
        删除所有对话及其消息（危险操作）。
        
        Returns:
            删除的对话数量
            
        Example:
            >>> deleted_count = service.delete_all_conversations()
            >>> print(f"删除了 {deleted_count} 个对话")
        """
        try:
            conversations = self._db.get_all_conversations()
            count = 0
            
            for conv in conversations:
                if self._db.delete_conversation(conv["id"]):
                    count += 1
            
            logger.info(f"已删除所有对话: {count} 个")
            return count
        except Exception as e:
            logger.error(f"删除所有对话失败: {e}")
            raise
    
    def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """获取对话消息
        
        获取指定对话的消息列表。
        
        Args:
            conversation_id: 对话 ID
            limit: 限制返回数量，默认返回全部
            
        Returns:
            消息列表
            
        Example:
            >>> messages = service.get_conversation_messages("conv-uuid-123")
            >>> for msg in messages:
            ...     print(f"{msg['role']}: {msg['content'][:50]}...")
        """
        try:
            return self._db.get_messages_by_conversation(conversation_id, limit=limit)
        except Exception as e:
            logger.error(f"获取对话消息失败: {e}")
            raise
    
    def get_recent_messages(
        self,
        conversation_id: str,
        n: int = 10,
    ) -> list[dict[str, Any]]:
        """获取最近的消息
        
        获取指定对话最近的 N 条消息（用于构建对话历史）。
        
        Args:
            conversation_id: 对话 ID
            n: 消息数量（轮数 * 2，因为每轮包含 user 和 assistant）
            
        Returns:
            消息列表，按时间正序排列
            
        Example:
            >>> messages = service.get_recent_messages("conv-uuid-123", n=10)
            >>> # 返回最近 5 轮对话（10 条消息）
        """
        try:
            return self._db.get_recent_messages(conversation_id, n=n)
        except Exception as e:
            logger.error(f"获取最近消息失败: {e}")
            raise
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """检查对话是否存在
        
        Args:
            conversation_id: 对话 ID
            
        Returns:
            是否存在
            
        Example:
            >>> if service.conversation_exists("conv-uuid-123"):
            ...     print("对话存在")
        """
        try:
            return self._db.get_conversation(conversation_id) is not None
        except Exception as e:
            logger.error(f"检查对话存在性失败: {e}")
            return False


# 全局 ConversationService 实例（单例模式）
_conversation_service_instance: Optional[ConversationService] = None


def get_conversation_service(
    db: Optional[Database] = None,
    settings: Optional[Settings] = None,
) -> ConversationService:
    """获取 ConversationService 实例（单例模式）
    
    使用单例模式避免重复创建服务实例，提高性能。
    
    Args:
        db: 数据库实例
        settings: 应用配置
        
    Returns:
        ConversationService 实例
        
    Example:
        >>> from backend.services.conversation_service import get_conversation_service
        >>> service = get_conversation_service()
        >>> conversation = service.create_conversation(title="新对话")
    """
    global _conversation_service_instance
    if _conversation_service_instance is None:
        _conversation_service_instance = ConversationService(
            db=db,
            settings=settings,
        )
    return _conversation_service_instance


def reset_conversation_service() -> None:
    """重置全局 ConversationService 实例
    
    用于测试或需要重新初始化服务的场景。
    """
    global _conversation_service_instance
    _conversation_service_instance = None
