"""
RAG 知识库助手 - 数据库模块

提供 SQLite 数据库的初始化和 CRUD 操作封装。
"""

from backend.db.database import Database, get_database

__all__ = ["Database", "get_database"]
