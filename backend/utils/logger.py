"""
RAG 知识库助手 - 日志配置模块

提供统一的日志配置和日志记录器获取接口。
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from backend.config.settings import get_settings


def get_logger(
    name: str,
    level: Optional[int] = None,
    log_to_file: bool = False,
) -> logging.Logger:
    """获取配置好的日志记录器
    
    Args:
        name: 日志记录器名称，通常使用 __name__
        level: 日志级别，默认从 settings.debug 推断
        log_to_file: 是否同时输出到文件
        
    Returns:
        logging.Logger: 配置好的日志记录器
        
    Example:
        >>> from backend.utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("这是一条信息日志")
        >>> logger.error("这是一条错误日志")
    """
    logger = logging.getLogger(name)
    
    # 设置日志级别
    if level is None:
        settings = get_settings()
        level = logging.DEBUG if settings.debug else logging.INFO
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_to_file:
        settings = get_settings()
        log_dir = settings.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / "app.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def configure_root_logger(
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
) -> None:
    """配置根日志记录器
    
    用于应用启动时统一配置所有日志。
    
    Args:
        level: 日志级别
        log_dir: 日志文件目录，为 None 则不输出到文件
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / "app.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
