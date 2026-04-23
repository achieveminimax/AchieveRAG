"""
RAG 知识库助手 - FastAPI 应用入口

应用主入口，负责：
- 初始化 FastAPI 应用
- 配置 CORS 中间件
- 配置生命周期管理
- 注册路由
- 配置全局异常处理
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config.settings import get_settings
from backend.db.database import init_database
from backend.routers import chat, conversations, documents, settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理
    
    启动时执行：
    - 初始化数据库表结构
    - 创建必要的目录
    
    关闭时执行：
    - 清理资源
    """
    # 启动时执行
    logger.info("应用启动中...")
    
    try:
        # 初始化数据库
        db = init_database()
        logger.info("数据库初始化完成")
        
        # 创建必要的目录
        settings_obj = get_settings()
        settings_obj.upload_dir.mkdir(parents=True, exist_ok=True)
        settings_obj.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        settings_obj.log_dir.mkdir(parents=True, exist_ok=True)
        logger.info("目录结构初始化完成")
        
    except Exception as e:
        logger.error(f"启动初始化失败: {e}")
        raise
    
    logger.info("应用启动完成")
    yield
    
    # 关闭时执行
    logger.info("应用关闭中...")
    # 这里可以添加资源清理逻辑
    logger.info("应用已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例
    
    Returns:
        FastAPI 应用实例
    """
    settings_obj = get_settings()
    
    app = FastAPI(
        title=settings_obj.app_name,
        version=settings_obj.app_version,
        description="基于 RAG 技术的个人知识库问答系统",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # 配置 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings_obj.cors_allow_origins,
        allow_credentials=settings_obj.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(documents.router, prefix="/api")
    app.include_router(chat.router)
    app.include_router(conversations.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    
    # 配置全局异常处理
    configure_exception_handlers(app)
    
    return app


def configure_exception_handlers(app: FastAPI) -> None:
    """配置全局异常处理器
    
    统一返回格式：
    {
        "code": 错误码,
        "message": 错误消息,
        "detail": 详细错误信息（可选）
    }
    """
    
    @app.exception_handler(400)
    async def bad_request_handler(request: Request, exc: Any):
        """处理 400 错误"""
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "请求参数错误",
                "detail": str(exc.detail) if hasattr(exc, "detail") else str(exc),
            },
        )
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Any):
        """处理 404 错误"""
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "message": "资源不存在",
                "detail": str(exc.detail) if hasattr(exc, "detail") else str(exc),
            },
        )
    
    @app.exception_handler(422)
    async def validation_error_handler(request: Request, exc: Any):
        """处理请求参数校验错误"""
        detail = exc.errors() if hasattr(exc, "errors") else str(exc)
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数校验失败",
                "detail": detail,
            },
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Any):
        """处理 500 错误"""
        logger.error(f"内部服务器错误: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "detail": "请稍后重试或联系管理员",
            },
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """处理所有未捕获的异常"""
        logger.error(f"未捕获的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "detail": str(exc) if get_settings().debug else "请稍后重试或联系管理员",
            },
        )


# 创建应用实例
app = create_app()


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": "healthy",
        },
    }


project_root = Path(__file__).resolve().parents[1]
frontend_dir = project_root / "frontend"
if frontend_dir.exists() and (frontend_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    
    settings_obj = get_settings()
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings_obj.debug,
    )
