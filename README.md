# RAG 知识库助手（RAG Knowledge Assistant）

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-green" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License">
</p>

基于 **Retrieval-Augmented Generation（RAG，检索增强生成）** 的个人知识库问答应用。支持上传文档（PDF/Markdown/TXT/DOCX），自动完成解析→分块→向量化索引，并通过 FastAPI 提供智能问答接口（支持 SSE 流式输出），前端为原生 HTML/CSS/JavaScript 单页应用（SPA）。

---

## 📑 目录

- [功能特性](#-功能特性)
- [技术架构](#-技术架构)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [API 文档](#-api-文档)
- [前端界面](#-前端界面)
- [部署指南](#-部署指南)
- [开发指南](#-开发指南)
- [常见问题](#-常见问题)
- [更新日志](#-更新日志)

---

## ✨ 功能特性

### 核心功能

| 功能模块 | 功能描述 | 状态 |
|----------|----------|------|
| 📄 **多格式文档支持** | PDF、Markdown、TXT、DOCX 自动解析 | ✅ |
| 🔍 **智能问答** | 基于向量检索 + LLM 生成回答 | ✅ |
| 💬 **流式对话** | SSE 实时流式输出，逐 token 渲染 | ✅ |
| 📎 **来源引用** | 回答附带来源文档和页码引用 | ✅ |
| 📚 **知识库管理** | 文档上传、列表、删除、统计、预览 | ✅ |
| 💾 **对话历史** | 保存、继续、删除历史对话 | ✅ |
| ⚙️ **系统设置** | 模型参数、检索参数可配置 | ✅ |

### 技术亮点

- **来源多样性优化**: RAG 检索时按来源交叉采样，避免单文档垄断结果
- **内容去重**: 自动去除重复上传文档的重复 chunk
- **智能文档查询**: 支持自然语言查询知识库中的文档列表
- **Token 缓冲发送**: SSE 流式输出时批量发送，减少网络开销
- **一体化托管**: 后端可直接挂载并托管前端静态文件，单端口部署

---

## 🏗️ 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│               前端 (HTML + CSS + JavaScript)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ 智能问答  │  │ 知识库管理│  │ 对话历史  │  │ 系统设置 │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
└───────┼──────────────┼──────────────┼──────────────┼─────┘
        │   HTTP REST API (JSON / SSE)                   │
        ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│               后端 API 服务 (FastAPI)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ 文档处理  │  │ RAG 链路  │  │ 对话管理  │  │ 配置管理 │ │
│  │  路由    │  │  编排    │  │  路由    │  │  路由   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
└───────┼──────────────┼──────────────┼──────────────┼─────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                      数据层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ ChromaDB │  │  SQLite  │  │ 本地文件  │              │
│  │ (向量库) │  │ (关系库) │  │  存储    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                    外部服务                              │
│  ┌──────────────┐  ┌──────────────────────────────┐     │
│  │ OpenAI API   │  │ 其他 OpenAI 兼容服务          │     │
│  │ (LLM+Embed)  │  │                              │     │
│  └──────────────┘  └──────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **后端框架** | FastAPI + Uvicorn | 异步 Web 框架，原生 SSE 支持 |
| **RAG 编排** | LangChain | RAG 链路编排 |
| **LLM** | OpenAI GPT-4o-mini | 性价比高，效果好 |
| **Embedding** | OpenAI text-embedding-3-small | 高质量文本向量化 |
| **向量数据库** | ChromaDB | 轻量级，本地持久化 |
| **关系数据库** | SQLite | 内置，无需额外安装 |
| **前端** | HTML5 + CSS3 + 原生 JavaScript | SPA 单页应用，无框架依赖 |

---

## 📁 项目结构

```
rag-knowledge-assistant/
├── .env                          # 环境变量配置（API Key 等）
├── .env.example                  # 环境变量模板
├── .gitignore                    # Git 忽略配置
├── pyproject.toml                # 项目依赖和元数据
├── README.md                     # 项目说明文档
├── requirements.txt              # Python 后端依赖清单
├── requirements-prod.txt         # 生产环境依赖
├── render.yaml                   # Render 部署配置
├── vercel.json                   # Vercel 部署配置
├── AGENTS.md                     # 项目规范文档
│
├── backend/                      # 后端服务目录
│   ├── main.py                   # FastAPI 应用入口
│   ├── config/                   # 配置模块
│   │   ├── __init__.py
│   │   └── settings.py           # Pydantic 配置定义
│   ├── core/                     # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── document_loader.py    # 文档加载与解析
│   │   ├── text_splitter.py      # 文本分块
│   │   ├── embeddings.py         # Embedding 封装
│   │   ├── vectorstore.py        # 向量数据库操作
│   │   ├── rag_chain.py          # RAG 链路编排
│   │   └── llm_client.py         # LLM 客户端封装
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic 数据模型
│   ├── db/                       # 数据库操作
│   │   ├── __init__.py
│   │   └── database.py           # SQLite 操作封装
│   ├── routers/                  # API 路由
│   │   ├── __init__.py
│   │   ├── documents.py          # 文档管理 API
│   │   ├── chat.py               # 问答对话 API（含 SSE）
│   │   ├── conversations.py      # 对话历史 API
│   │   └── settings.py           # 系统设置 API
│   ├── services/                 # 业务服务层
│   │   ├── __init__.py
│   │   ├── document_service.py   # 文档处理服务
│   │   ├── rag_service.py        # RAG 问答服务
│   │   └── conversation_service.py # 对话管理服务
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       └── logger.py             # 日志配置
│
├── frontend/                     # 前端目录
│   ├── index.html                # 主页面入口（SPA 骨架）
│   ├── css/
│   │   ├── style.css             # 全局样式、设计系统变量
│   │   ├── components.css        # 通用组件样式
│   │   ├── chat.css              # 对话页面样式
│   │   ├── upload.css            # 知识库管理页面样式
│   │   ├── history.css           # 对话历史页面样式
│   │   └── settings.css          # 设置页面样式
│   ├── js/
│   │   ├── app.js                # 应用入口、路由管理、全局状态
│   │   ├── api.js                # 后端 API 请求封装（fetch + SSE）
│   │   ├── components.js         # 通用组件（Toast、Confirm Dialog）
│   │   ├── chat.js               # 对话功能模块
│   │   ├── upload.js             # 文档上传模块
│   │   ├── history.js            # 对话历史模块
│   │   ├── settings.js           # 设置页面模块
│   │   └── document-preview.js   # 文档预览模块
│   └── assets/
│       └── icons/                # SVG 图标文件
│
├── data/                         # 数据目录（运行后生成）
│   ├── uploads/                  # 上传文件存储
│   ├── chroma_db/               # ChromaDB 持久化目录
│   └── app.db                    # SQLite 数据库文件
│
├── tests/                        # 测试目录
│   ├── __init__.py
│   ├── test_document_loader.py   # 文档加载器测试
│   ├── test_text_splitter.py     # 文本分块测试
│   ├── test_embeddings.py        # Embedding 测试
│   ├── test_vectorstore.py       # 向量存储测试
│   ├── test_database.py          # 数据库测试
│   └── test_settings.py          # 配置管理测试
│
└── scripts/                      # 辅助脚本
    └── init_db.py                # 数据库初始化脚本
```

### 关键文件说明

| 文件路径 | 说明 |
|----------|------|
| [`backend/main.py`](backend/main.py) | FastAPI 应用入口，路由注册、生命周期管理 |
| [`backend/config/settings.py`](backend/config/settings.py) | Pydantic Settings 配置定义 |
| [`frontend/index.html`](frontend/index.html) | SPA 主页面 |
| [`frontend/js/api.js`](frontend/js/api.js) | API 请求封装，含 SSE 处理 |

---

## 🚀 快速开始

### 环境要求

- **Python**: >= 3.10（推荐 3.11）
- **OpenAI API Key**: 用于 LLM + Embedding（或任意 OpenAI 兼容服务）

### 安装步骤

#### 1. 克隆项目

```bash
cd /Users/achieve/Documents/Trae_Projects/Projects/RAG个人助手
```

#### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置环境变量

复制模板文件并修改：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置以下项：

```bash
# 必填：OpenAI API Key
OPENAI_API_KEY=sk-your-api-key-here

# 可选：OpenAI Base URL（默认 https://api.openai.com/v1）
# 可替换为任意 OpenAI 兼容服务地址
OPENAI_BASE_URL=https://api.openai.com/v1
```

可选配置（不填则复用 OpenAI 配置）：

```bash
# Embedding 独立配置（如需使用不同的 Embedding 服务）
EMBEDDING_API_KEY=sk-your-embedding-key
EMBEDDING_BASE_URL=https://your-embedding-service.com/v1
```

#### 5. 初始化数据库（可选但推荐）

```bash
python scripts/init_db.py
```

#### 6. 启动服务

**方式 A：前后端分离开发（推荐开发时使用）**

启动后端：

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

启动前端（另开终端）：

```bash
cd frontend
python -m http.server 3000
```

访问：`http://localhost:3000`

**方式 B：后端一体化托管（推荐生产环境）**

```bash
python -m backend.main
# 或
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

访问：`http://localhost:8000`

> 说明：启动时会自动创建必要目录（uploads/chroma_db/logs）并初始化数据库表结构。

### 验证安装

- **Swagger 文档**: `http://localhost:8000/docs`
- **ReDoc 文档**: `http://localhost:8000/redoc`
- **健康检查**: `http://localhost:8000/health`

---

## ⚙️ 配置说明

配置由 Pydantic Settings 从环境变量与 `.env` 文件加载，完整配置见 [`backend/config/settings.py`](backend/config/settings.py)。

### 常用配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key | 必填 |
| `OPENAI_BASE_URL` | OpenAI Base URL | `https://api.openai.com/v1` |
| `EMBEDDING_API_KEY` | Embedding API Key（可选） | 复用 OpenAI |
| `EMBEDDING_BASE_URL` | Embedding Base URL（可选） | 复用 OpenAI |
| `LLM_MODEL` | LLM 模型名称 | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | 生成温度 | `0.7` |
| `LLM_MAX_TOKENS` | 最大生成 Token 数 | `2048` |
| `EMBEDDING_MODEL` | Embedding 模型 | `text-embedding-3-small` |
| `DEFAULT_TOP_K` | 默认检索文档数 | `5` |
| `SIMILARITY_THRESHOLD` | 相似度阈值 | `0.0` |
| `CHUNK_SIZE` | 文本分块大小 | `512` |
| `CHUNK_OVERLAP` | 文本分块重叠大小 | `50` |
| `MAX_CHAT_HISTORY` | 最大对话历史轮数 | `10` |
| `DATA_DIR` | 数据目录 | `./data` |
| `CORS_ALLOW_ORIGINS` | CORS 允许的来源 | `*` |

### 完整配置示例

```bash
# .env 完整示例

# OpenAI 配置
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# Embedding 配置（可选，默认复用 OpenAI）
# EMBEDDING_API_KEY=sk-your-embedding-key
# EMBEDDING_BASE_URL=https://api.openai.com/v1

# 模型配置
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
EMBEDDING_MODEL=text-embedding-3-small

# 检索配置
DEFAULT_TOP_K=5
SIMILARITY_THRESHOLD=0.0
CHUNK_SIZE=512
CHUNK_OVERLAP=50
MAX_CHAT_HISTORY=10

# 路径配置
DATA_DIR=./data

# CORS 配置
CORS_ALLOW_ORIGINS=*
CORS_ALLOW_CREDENTIALS=false
```

---

## 📚 API 文档

### 文档管理 API

实现：[`backend/routers/documents.py`](backend/routers/documents.py)

#### 上传文档

```http
POST /api/documents/upload
Content-Type: multipart/form-data
```

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| files | File | 是 | 要上传的文件列表，支持多文件 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "success": [
      {
        "document_id": "doc-xxx",
        "filename": "example.pdf",
        "chunk_count": 15
      }
    ],
    "failed": []
  }
}
```

#### 获取文档列表

```http
GET /api/documents
```

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "documents": [
      {
        "id": "doc-xxx",
        "filename": "example.pdf",
        "file_size": 1024000,
        "file_type": "pdf",
        "chunk_count": 15,
        "status": "completed",
        "created_at": "2024-01-01T00:00:00"
      }
    ],
    "total": 1
  }
}
```

#### 获取文档统计

```http
GET /api/documents/stats
```

#### 获取文档详情

```http
GET /api/documents/{doc_id}
```

#### 获取文档预览内容

```http
GET /api/documents/{doc_id}/content
```

#### 删除文档

```http
DELETE /api/documents/{doc_id}
```

### 问答对话 API

实现：[`backend/routers/chat.py`](backend/routers/chat.py)

#### 流式问答（SSE）

```http
POST /api/chat/ask
Content-Type: application/json
```

**请求体**:

```json
{
  "question": "什么是 RAG 技术？",
  "conversation_id": "conv-xxx",  // 可选，不传则创建新对话
  "top_k": 5,                     // 可选，检索文档数量
  "document_ids": ["doc-xxx"]     // 可选，指定检索的文档
}
```

**SSE 事件类型**:

| 事件类型 | 说明 | 数据格式 |
|----------|------|----------|
| `token` | 生成的文本片段 | `{"content": "..."}` |
| `sources` | 来源引用列表 | `{"sources": [...]}` |
| `done` | 完成事件 | `{"conversation_id": "...", "message_id": "..."}` |
| `error` | 错误事件 | `{"message": "..."}` |

**JavaScript 调用示例**:

```javascript
const eventSource = new EventSource('/api/chat/ask', {
  method: 'POST',
  body: JSON.stringify({question: "什么是 RAG？"})
});

eventSource.addEventListener('token', (e) => {
  const data = JSON.parse(e.data);
  console.log('收到内容:', data.content);
});

eventSource.addEventListener('done', (e) => {
  const data = JSON.parse(e.data);
  console.log('对话ID:', data.conversation_id);
  eventSource.close();
});
```

#### 同步问答

```http
POST /api/chat/ask/sync
Content-Type: application/json
```

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "conversation_id": "conv-xxx",
    "message_id": "msg-xxx",
    "answer": "RAG（检索增强生成）是一种...",
    "sources": [
      {
        "source": "example.pdf",
        "page": 5,
        "score": 0.89,
        "text": "..."
      }
    ]
  }
}
```

#### 重新生成回答

```http
POST /api/chat/regenerate?conversation_id=conv-xxx&message_id=msg-xxx
```

### 对话历史 API

实现：[`backend/routers/conversations.py`](backend/routers/conversations.py)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/conversations` | 创建对话 |
| GET | `/api/conversations` | 获取对话列表 |
| GET | `/api/conversations/{id}` | 获取对话详情（含消息） |
| PUT | `/api/conversations/{id}` | 更新对话标题 |
| DELETE | `/api/conversations/{id}` | 删除单个对话 |
| DELETE | `/api/conversations` | 清空全部对话 |

### 系统设置 API

实现：[`backend/routers/settings.py`](backend/routers/settings.py)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 获取当前配置 |
| PUT | `/api/settings` | 更新配置 |
| GET | `/api/settings/models` | 获取可用模型列表 |
| GET | `/api/settings/stats` | 获取系统统计 |

---

## 🎨 前端界面

### 页面结构

- **智能问答页**: 对话界面，支持 SSE 流式输出、来源引用展示
- **知识库管理页**: 文档上传、列表、删除、预览、统计
- **对话历史页**: 历史对话列表、删除、继续对话
- **系统设置页**: 模型参数、检索参数配置

### 前端 API BaseURL 覆盖

默认逻辑见 [`frontend/js/api.js`](frontend/js/api.js)，优先级从高到低：

1. `window.RAG_API_BASE_URL`
2. `window.__RAG_APP_CONFIG__?.apiBaseURL`
3. `localStorage['rag_api_base_url']`
4. 自动推断：开发端口（3000/3001/8080）使用 `http(s)://127.0.0.1:8000/api`；否则使用 `${window.location.origin}/api`

---

## 🌐 部署指南

### Render 部署

项目包含 [`render.yaml`](render.yaml) 配置文件：

- **构建**: `pip install -r requirements-prod.txt`
- **启动**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **持久化磁盘**: 挂载到 `/var/data` 并设置 `DATA_DIR=/var/data`（用于 SQLite/Chroma/uploads）

### Vercel（静态前端）

仓库包含 [`vercel.json`](vercel.json)（用于 SPA 路由重写）。如仅部署前端，请确保后端 API 可从外网访问，并在前端注入 `window.RAG_API_BASE_URL` 指向后端地址。

### Docker 部署（示例）

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🛠️ 开发指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_document_loader.py

# 运行 API 测试
pytest tests/test_api/

# 生成覆盖率报告
pytest --cov=backend --cov-report=html
```

### 代码规范

- 遵循 **PEP 8** 规范
- 所有函数添加 **type hints**
- 所有公共模块添加 **docstring**
- 使用 **Pydantic** 进行数据校验

### 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

---

## ❓ 常见问题

### Q: 上传文档后问答没有使用文档内容？

A: 请检查：
1. 文档是否上传成功（查看文档列表状态是否为 `completed`）
2. API Key 是否配置正确
3. 向量数据库是否正常（查看 `data/chroma_db/` 目录）

### Q: 如何切换 LLM 模型？

A: 修改 `.env` 文件中的 `LLM_MODEL` 配置，或在系统设置页面修改。支持的模型包括：
- `gpt-4o-mini`（推荐，性价比高）
- `gpt-4o`（更强的推理能力）
- `gpt-3.5-turbo`（速度快，成本低）

### Q: 如何部署到公网？

A: 推荐方案：
1. **Render**: 使用项目自带的 `render.yaml` 一键部署
2. **Vercel + 自建后端**: 前端部署到 Vercel，后端部署到云服务器
3. **Docker**: 使用 Docker 打包部署到任意云平台

### Q: 支持哪些 Embedding 模型？

A: 默认使用 OpenAI 的 `text-embedding-3-small`，也支持：
- `text-embedding-3-large`
- `text-embedding-ada-002`

可通过 `EMBEDDING_MODEL` 环境变量配置。

---

## 📝 更新日志

### v1.0.0 (2026-04-23)

- ✅ 完整实现 RAG 知识库问答功能
- ✅ 支持 PDF/Markdown/TXT/DOCX 多格式文档
- ✅ SSE 流式输出，逐 token 渲染
- ✅ 来源引用展示
- ✅ 对话历史管理
- ✅ 系统设置页面
- ✅ 前后端一体化部署

---

## 📄 License

MIT License

---

<p align="center">
  Made with ❤️ by RAG Knowledge Assistant Team
</p>
