"""
RAG 知识库助手 - 配置模块

提供统一的配置管理入口，支持从环境变量和 .env 文件加载配置。

Usage:
    >>> from config import get_settings, Settings
    >>> settings = get_settings()
    >>> print(settings.llm_model)
    'gpt-4o-mini'
    
    >>> from config import settings
    >>> print(settings.openai_api_key)
"""

from backend.config.settings import Settings, get_settings, reload_settings, settings

__all__ = [
    "Settings",
    "get_settings",
    "reload_settings",
    "settings",
]
