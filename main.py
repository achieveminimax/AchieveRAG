"""
Vercel FastAPI 入口文件。

Vercel 会在项目根目录查找 `main.py` 并读取全局变量 `app`。
"""

from backend.main import app

