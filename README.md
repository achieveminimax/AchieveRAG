# RAG 知识库助手（RAG Knowledge Assistant）

基于 Retrieval-Augmented Generation（RAG，检索增强生成）的个人知识库问答应用：支持上传文档（PDF/Markdown/TXT/DOCX），自动解析→分块→向量化索引，并通过 FastAPI 提供问答接口（支持 SSE 流式输出），前端为原生 HTML/CSS/JavaScript SPA。

- 后端入口：[`backend/main.py`](backend/main.py)
- 前端入口：[`frontend/index.html`](frontend/index.html)
- 配置定义：[`backend/config/settings.py`](backend/config/settings.py)

## 功能特性

- 多格式文档：PDF、Markdown、TXT、DOCX（限制扩展名与上传大小）
- 知识库管理：上传、列表、删除、统计、内容预览
- 智能问答：SSE 流式输出 `/api/chat/ask` + 同步接口 `/api/chat/ask/sync`
- 对话历史：创建、列表、详情、改标题、删除/清空
- 系统设置：读取/更新模型与检索参数、运行配置
- 一体化托管：后端可直接挂载并托管 `frontend/` 静态文件（无需单独起前端服务）

## 技术栈

- 后端：FastAPI + Uvicorn
- RAG：LangChain + ChromaDB（本地持久化）
- LLM/Embedding：OpenAI 兼容接口（`openai` SDK）
- 数据：SQLite（默认 `data/app.db`）
- 前端：原生 HTML/CSS/JavaScript（无构建、无 npm）

## 目录结构（简要）

```
.
├── backend/          # FastAPI 后端、RAG 核心逻辑
├── frontend/         # 原生 SPA
├── data/             # uploads / chroma_db / app.db（运行后生成/持久化）
├── scripts/init_db.py
├── requirements.txt
└── .env.example
```

## 快速开始（本地开发）

### 1）准备环境

- Python >= 3.10（推荐 3.11）
- OpenAI 兼容 API Key（用于 LLM + Embedding）

### 2）安装依赖

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 3）配置环境变量

复制模板并按需修改：

```bash
cp .env.example .env
```

至少需要配置：

- `OPENAI_API_KEY`（必填）
- `OPENAI_BASE_URL`（默认 `https://api.openai.com/v1`，可替换为任意 OpenAI 兼容服务地址）

可选配置（不填则回退复用 OpenAI 配置）：

- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`

### 4）初始化数据库（可选但推荐）

```bash
python scripts/init_db.py
```

### 5）启动后端（推荐从项目根目录启动）

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

说明：

- 启动时会自动创建必要目录（uploads/chroma_db/logs）并初始化数据库表结构（见 `backend/main.py` 的 lifespan）。
- 若检测到 `frontend/index.html` 存在，会将 `frontend/` 作为静态站点挂载到 `/`（见 `backend/main.py`）。

### 6）启动前端（两种方式）

方式 A：前后端分离开发（推荐）

```bash
cd frontend
python -m http.server 3000
```

访问：`http://localhost:3000`

前端在 3000/3001/8080 端口下会自动把 API Base 指向 `http(s)://127.0.0.1:8000/api`（逻辑见 `frontend/js/api.js`）。

方式 B：后端一体化托管前端（无需单独起前端服务）

直接访问：`http://localhost:8000`

## 配置说明（Settings）

配置由 Pydantic Settings 从环境变量与 `.env` 加载（见 [`backend/config/settings.py`](backend/config/settings.py)），常用项：

- OpenAI/兼容服务：`OPENAI_API_KEY`、`OPENAI_BASE_URL`
- 模型与生成：`LLM_MODEL`、`LLM_TEMPERATURE`、`LLM_MAX_TOKENS`
- Embedding：`EMBEDDING_MODEL`、`EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL`
- 检索与分块：`DEFAULT_TOP_K`、`SIMILARITY_THRESHOLD`、`CHUNK_SIZE`、`CHUNK_OVERLAP`
- 路径与持久化：`DATA_DIR`、`UPLOAD_DIR`、`CHROMA_PERSIST_DIR`、`DB_PATH`
- CORS：`CORS_ALLOW_ORIGINS`（逗号分隔）、`CORS_ALLOW_CREDENTIALS`

## API 概览

路由注册见：[`backend/main.py`](backend/main.py)

### 文档管理 `/api/documents`

实现：[`backend/routers/documents.py`](backend/routers/documents.py)

- `POST /api/documents/upload`：多文件上传并处理（解析/分块/入库）
- `GET  /api/documents`：文档列表
- `GET  /api/documents/stats`：统计信息
- `GET  /api/documents/{doc_id}`：文档详情
- `GET  /api/documents/{doc_id}/content`：文档预览（可能截断）
- `DELETE /api/documents/{doc_id}`：删除文档（含向量分块与本地文件）

### 问答 `/api/chat`

实现：[`backend/routers/chat.py`](backend/routers/chat.py)

- `POST /api/chat/ask`：SSE 流式问答（`text/event-stream`）
- `POST /api/chat/ask/sync`：同步问答
- `POST /api/chat/regenerate?conversation_id=...&message_id=...&top_k=...`：SSE 重新生成

SSE 事件类型：

- `token`：`{"content": "..."}`
- `sources`：`{"sources": [...]}`（来源引用）
- `done`：`{"conversation_id": "...", "message_id": "..."}`
- `error`：`{"message": "..."}`

### 对话历史 `/api/conversations`

实现：[`backend/routers/conversations.py`](backend/routers/conversations.py)

- `POST   /api/conversations`：创建对话
- `GET    /api/conversations`：对话列表
- `GET    /api/conversations/{conversation_id}`：对话详情（含消息）
- `PUT    /api/conversations/{conversation_id}`：更新标题
- `DELETE /api/conversations/{conversation_id}`：删除单个对话
- `DELETE /api/conversations`：清空全部对话

### 系统设置 `/api/settings`

实现：[`backend/routers/settings.py`](backend/routers/settings.py)

- `GET /api/settings`：获取当前配置（包含是否已配置 Key、默认值等）
- `PUT /api/settings`：更新配置（部分项可能需要重启后生效）

## 前端 API BaseURL 覆盖方式

默认逻辑见：[`frontend/js/api.js`](frontend/js/api.js)

优先级从高到低：

1. `window.RAG_API_BASE_URL`
2. `window.__RAG_APP_CONFIG__?.apiBaseURL`
3. `localStorage['rag_api_base_url']`
4. 自动推断：开发端口（3000/3001/8080）使用 `http(s)://127.0.0.1:8000/api`；否则使用 `${window.location.origin}/api`

## 测试

```bash
pytest
pytest tests/test_api/
pytest --cov=backend --cov-report=html
```

测试配置见：[`pyproject.toml`](pyproject.toml)

## 部署

### Render

项目包含 [`render.yaml`](render.yaml)：

- 构建：`pip install -r requirements-prod.txt`
- 启动：`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- 持久化磁盘：挂载到 `/var/data` 并设置 `DATA_DIR=/var/data`（用于 SQLite/Chroma/uploads）

### Vercel（静态前端）

仓库包含 [`vercel.json`](vercel.json)（用于 SPA 路由重写）。如仅部署前端，请确保后端 API 可从外网访问，并在前端注入 `window.RAG_API_BASE_URL` 指向后端地址。

## License

MIT

