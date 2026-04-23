"""
RAG 知识库助手 - 配置管理模块

使用 Pydantic Settings 管理应用配置，支持从环境变量和 .env 文件加载配置。
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类
    
    所有配置项均可通过环境变量或 .env 文件设置。
    环境变量名自动转换为大写，如：openai_api_key -> OPENAI_API_KEY
    """
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        env_prefix="",  # 无前缀，直接使用配置项名称的大写形式
    )
    
    # === OpenAI API 配置 ===
    openai_api_key: str = Field(..., description="OpenAI API Key")

    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API 基础 URL",
    )

    # === Embedding API 配置（阿里云百炼） ===
    embedding_api_key: Optional[str] = Field(
        default=None,
        description="Embedding API Key",
    )

    embedding_base_url: Optional[str] = Field(
        default=None,
        description="Embedding API 基础 URL",
    )

    # === MiniMax Group ID 配置 ===
    minimax_group_id: Optional[str] = Field(
        default=None,
        description="MiniMax Group ID",
    )

    # === LLM 模型配置 ===
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="LLM 模型名称",
    )
    
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM Temperature 参数（0-2）",
    )
    
    llm_max_tokens: int = Field(
        default=2048,
        ge=1,
        le=8192,
        description="LLM 最大生成 Token 数",
    )
    
    # === Embedding 模型配置 ===
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding 模型名称",
    )
    
    # === 检索配置 ===
    default_top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="默认检索返回的文档数（Top-K）",
    )
    
    similarity_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="相似度阈值，低于此值的检索结果将被过滤",
    )
    
    # === 文本分块配置 ===
    chunk_size: int = Field(
        default=512,
        ge=100,
        le=2000,
        description="文本分块大小（字符数）",
    )
    
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=500,
        description="文本分块重叠大小（字符数）",
    )
    
    # === 应用配置 ===
    app_name: str = Field(
        default="RAG 知识库助手",
        description="应用名称",
    )
    
    app_version: str = Field(
        default="1.0.0",
        description="应用版本",
    )
    
    debug: bool = Field(
        default=False,
        description="调试模式",
    )

    cors_allow_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:8080",
        ],
        description="CORS 允许的来源列表",
    )

    cors_allow_credentials: bool = Field(
        default=True,
        description="CORS 是否允许携带凭证",
    )
    
    # === 数据目录配置 ===
    data_dir: Path = Field(
        default=Path("./data"),
        description="数据根目录",
    )
    
    upload_dir: Optional[Path] = Field(
        default=None,
        description="上传文件存储目录",
    )
    
    chroma_persist_dir: Optional[Path] = Field(
        default=None,
        description="ChromaDB 持久化目录",
    )
    
    db_path: Optional[Path] = Field(
        default=None,
        description="SQLite 数据库文件路径",
    )
    
    log_dir: Optional[Path] = Field(
        default=None,
        description="日志文件存储目录",
    )
    
    # === 文件上传配置 ===
    max_file_size: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        ge=1,
        le=100 * 1024 * 1024,  # 100MB
        description="单文件最大上传大小（字节）",
    )
    
    allowed_extensions: set[str] = Field(
        default={".pdf", ".md", ".txt", ".docx"},
        description="允许上传的文件扩展名集合",
    )
    
    # === 对话配置 ===
    max_chat_history: int = Field(
        default=10,
        ge=1,
        le=50,
        description="保留的最大对话历史轮数",
    )
    
    # === 字段校验器 ===
    
    @field_validator("upload_dir", "chroma_persist_dir", "db_path", "log_dir", mode="before")
    @classmethod
    def normalize_optional_paths(cls, v):
        """规范化可选路径字段"""
        if v is None:
            return None
        return Path(v)
    
    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v):
        """解析允许的文件扩展名"""
        if isinstance(v, str):
            # 支持逗号分隔的字符串，如 ".pdf,.md,.txt,.docx"
            return set(ext.strip().lower() for ext in v.split(",") if ext.strip())
        return v

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
    
    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v, info):
        """验证 chunk_overlap 不能超过 chunk_size"""
        chunk_size = info.data.get("chunk_size", 512)
        if v >= chunk_size:
            raise ValueError(f"chunk_overlap ({v}) 必须小于 chunk_size ({chunk_size})")
        return v

    @model_validator(mode="after")
    def apply_derived_defaults(self) -> "Settings":
        """应用依赖 data_dir 的默认路径与回退配置"""
        self.upload_dir = self.upload_dir or self.data_dir / "uploads"
        self.chroma_persist_dir = self.chroma_persist_dir or self.data_dir / "chroma_db"
        self.db_path = self.db_path or self.data_dir / "app.db"
        self.log_dir = self.log_dir or self.data_dir / "logs"
        self.embedding_api_key = self.embedding_api_key or self.openai_api_key
        self.embedding_base_url = self.embedding_base_url or self.openai_base_url
        return self
    
    # === 便捷属性 ===
    
    @property
    def max_file_size_mb(self) -> int:
        """返回最大文件大小（MB）"""
        return self.max_file_size // (1024 * 1024)
    
    @property
    def allowed_extensions_list(self) -> list[str]:
        """返回允许的文件扩展名列表（排序后）"""
        return sorted(list(self.allowed_extensions))
    
    def is_allowed_file(self, filename: str) -> bool:
        """检查文件名是否允许上传
        
        Args:
            filename: 文件名
            
        Returns:
            是否允许上传
        """
        ext = Path(filename).suffix.lower()
        return ext in self.allowed_extensions


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）
    
    使用 lru_cache 确保配置只加载一次，提高性能。
    
    Returns:
        Settings 配置实例
        
    Example:
        >>> from backend.config.settings import get_settings
        >>> settings = get_settings()
        >>> print(settings.llm_model)
        'gpt-4o-mini'
    """
    return Settings(_env_file=".env", _env_file_encoding="utf-8")


def reload_settings() -> Settings:
    """重新加载配置
    
    用于在运行时重新加载配置（如配置文件变更后）。
    
    Returns:
        新的 Settings 配置实例
    """
    get_settings.cache_clear()
    return get_settings()


# 导出默认配置实例（向后兼容）
# 注意：这里使用延迟加载，避免在导入时就尝试加载配置
_settings_instance: Optional[Settings] = None


def _get_settings_instance() -> Settings:
    """获取或创建默认配置实例"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = get_settings()
    return _settings_instance


# 使用 property 模拟模块级别的属性访问
class _SettingsProxy:
    """配置代理类，用于支持从模块直接访问配置属性"""
    
    def __getattr__(self, name: str):
        return getattr(_get_settings_instance(), name)
    
    def __setattr__(self, name: str, value):
        raise AttributeError("Settings is read-only. Use environment variables or .env file.")


settings = _SettingsProxy()
