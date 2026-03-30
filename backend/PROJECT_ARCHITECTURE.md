# SuperMew 项目架构文档

## 一、项目概述

SuperMew 是一个基于 LangChain/LangGraph 的智能问答系统，支持 RAG（检索增强生成）、知识库管理、流式输出、实时思考链路展示、用户认证等功能。

---

## 二、技术栈

### 2.1 后端核心

| 技术 | 版本要求 | 用途 |
|------|----------|------|
| **FastAPI** | ≥0.115.0 | Web 框架 |
| **Uvicorn** | ≥0.30.0 | ASGI 服务器 |
| **LangChain** | ≥0.2.14 | LLM 应用框架 |
| **LangGraph** | ≥0.2.31 | Agent 状态图编排 |
| **LangChain Community** | ≥0.2.12 | 第三方集成 |
| **Pydantic** | ≥2.8.0 | 数据校验 |
| **SQLAlchemy** | ≥2.0.36 | ORM |
| **Redis** | ≥5.2.1 | 缓存层 |

### 2.2 数据库与向量库

| 技术 | 用途 |
|------|------|
| **MySQL / PostgreSQL** | 持久化存储（用户、会话、消息、父文档） |
| **Redis** | 热点数据缓存（会话列表、消息、父文档） |
| **Milvus** | 向量数据库（支持 Hybrid Search） |

### 2.3 前端

- **Vue 3** (CDN)
- **marked** - Markdown 渲染
- **highlight.js** - 代码高亮

### 2.4 依赖包

```
rich, fastapi, uvicorn, python-dotenv, requests
pymilvus, python-multipart, pydantic
langchain, langchain-core, langchain-community
langchain-text-splitters, langchain-openai, langgraph
pypdf, docx2txt, unstructured, openpyxl, tabulate
sqlalchemy, pymysql (或 psycopg2-binary), redis
passlib[bcrypt], python-jose[cryptography]
```

---

## 三、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (Vue 3 CDN)                       │
│                  http://127.0.0.1:8000/                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ SSE / HTTP
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI 后端 (8000)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   api    │  │   auth   │  │  agent   │  │  tools   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  models  │  │  cache   │  │database  │  │ schemas  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   MySQL/PG      │  │     Redis       │  │    Milvus      │
│    (5432)       │  │    (6379)       │  │   (19530)      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    LangChain / LangGraph     │
              │    Agent + RAG Pipeline      │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    LLM (阿里云 DashScope)     │
              │    OpenAI 兼容 API            │
              └───────────────────────────────┘
```

---

## 四、核心模块说明

### 4.1 backend/app.py

FastAPI 应用入口：
- CORS 中间件配置
- 静态文件挂载（前端）
- 数据库初始化
- 路由注册

### 4.2 backend/api.py

API 路由层，所有接口定义：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/auth/register` | POST | 用户注册 |
| `/auth/login` | POST | 用户登录 |
| `/auth/me` | GET | 获取当前用户 |
| `/sessions` | GET | 获取会话列表 |
| `/sessions/{id}` | GET | 获取会话消息 |
| `/sessions/{id}` | DELETE | 删除会话 |
| `/chat` | POST | 非流式聊天 |
| `/chat/stream` | POST | **流式聊天（SSE）** |
| `/documents` | GET | 文档列表（管理员） |
| `/documents/upload` | POST | 上传文档（管理员） |
| `/documents/{filename}` | DELETE | 删除文档（管理员） |

### 4.3 backend/auth.py

认证鉴权模块：
- JWT Token 生成与验证
- 密码哈希（PBKDF2-SHA256，兼容 bcrypt）
- 角色解析（admin / user）
- 依赖注入：`get_current_user`, `require_admin`

### 4.4 backend/agent.py

LangChain Agent 核心：
- `chat_with_agent()` - 非流式
- `chat_with_agent_stream()` - **流式输出**
- 会话记忆管理
- 消息摘要压缩

### 4.5 backend/rag_pipeline.py

RAG 工作流（LangGraph StateGraph）：

```
retrieve_initial → grade_documents → [generate_answer / rewrite_question]
                                                       │
                                                       ▼
                                              retrieve_expanded → END
```

关键节点：
- **retrieve_initial**: 初次检索（Hybrid Search）
- **grade_documents**: 相关性评估（结构化输出）
- **rewrite_question**: 查询重写（Step-back / HyDE）
- **retrieve_expanded**: 扩展检索

### 4.6 backend/embedding.py

向量化服务：
- **密集向量**: 调用外部 Embedding API（阿里云 DashScope）
- **稀疏向量**: 自实现 BM25 算法（中英文分词）

### 4.7 backend/milvus_client.py

Milvus 客户端：
- 集合定义（稠密 + 稀疏字段）
- **Hybrid Search**: 稠密 + 稀疏 + RRF 融合
- Rerank 集成（Jina API）

### 4.8 backend/milvus_writer.py

向量写入：
- 叶子分块（L3）写入 Milvus
- 稠密 + 稀疏向量同步生成

### 4.9 backend/document_loader.py

文档加载与分块：
- 支持 PDF、Word、Excel
- **三级滑动窗口分块**（L1 / L2 / L3）
- 层级元数据（chunk_id, parent_chunk_id, chunk_level）

### 4.10 backend/parent_chunk_store.py

父级分块存储：
- L1 / L2 分块写入 PostgreSQL
- Redis 缓存热点数据

### 4.11 backend/cache.py

Redis 缓存封装：
- 会话消息缓存
- 会话列表缓存
- 父文档缓存

### 4.12 backend/models.py

SQLAlchemy ORM 模型：
- `User` - 用户表
- `ChatSession` - 会话表
- `ChatMessage` - 消息表
- `ParentChunk` - 父级分块表

---

## 五、关键特性实现

### 5.1 流式输出 + 实时 RAG 步骤

**核心问题**: FastAPI 异步循环中调用同步 LangChain 工具时，无法直接推送"思考中"状态。

**解决方案**: `call_soon_threadsafe` 跨线程调度

```python
# tools.py
def set_rag_step_queue(queue):
    global _RAG_STEP_QUEUE, _RAG_STEP_LOOP
    _RAG_STEP_QUEUE = queue
    _RAG_STEP_LOOP = asyncio.get_running_loop()  # 主线程捕获 Loop

def emit_rag_step(icon, label):
    # 子线程安全调度回主 Loop
    _RAG_STEP_LOOP.call_soon_threadsafe(
        _RAG_STEP_QUEUE.put_nowait,
        {"icon": icon, "label": label}
    )
```

### 5.2 混合检索（Hybrid Search）

- **Dense**: 外部 Embedding API 生成 1536 维向量
- **Sparse**: 自研 BM25 稀疏向量（jieba 分词）
- **融合**: Milvus `AnnSearchRequest` + RRF (k=60)

### 5.3 Auto-merging Retriever

- 三级分块：L1(大) → L2(中) → L3(叶子)
- 检索时先召回 L3，满足阈值则自动合并父块（L3→L2→L1）
- 减少向量冗余，保留上下文聚合能力

### 5.4 查询重写体系

- **Step-back**: 生成泛化问题，理解核心概念
- **HyDE**: 生成假设性文档，以文搜文
- **路由选择**: LLM 判断使用哪种策略

### 5.5 终止功能

- 前端: `AbortController` 取消 fetch
- 后端: `agent_task.cancel()` 立即注入 `CancelledError`，关闭上游 LLM 连接

---

## 六、环境变量 (.env)

```env
# ===== 模型 =====
ARK_API_KEY=your_api_key
MODEL=qwen-plus
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDER=qwen-plus

# ===== Rerank（可选）=====
RERANK_MODEL=qwen-plus
RERANK_BINDING_HOST=https://your-rerank-host
RERANK_API_KEY=your_rerank_api_key

# ===== Milvus =====
MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION=embeddings_collection

# ===== 数据库 / 缓存 =====
DATABASE_URL=mysql+pymysql://root:123456@127.0.0.1:3306/langchain_app
REDIS_URL=redis://127.0.0.1:6379/0

# ===== 认证 =====
JWT_SECRET_KEY=your-secret-key
ADMIN_INVITE_CODE=supermew-admin-2026
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
PASSWORD_PBKDF2_ROUNDS=310000

# ===== 工具（可选）=====
AMAP_WEATHER_API=https://restapi.amap.com/v3/weather/weatherInfo
AMAP_API_KEY=your_amap_api_key
```

---

## 七、运行指南

### 7.1 依赖安装

```bash
# 方式 A：推荐（uv）
uv sync

# 方式 B：pip
python -m venv .venv
pip install -e .
```

### 7.2 启动中间件

**使用 Docker Compose（推荐）**:
```bash
docker compose up -d
```

启动：
- MySQL/PostgreSQL
- Redis
- Milvus (etcd, minio, standalone, attu)

**端口说明**:
- MySQL: 3306
- PostgreSQL: 5432
- Redis: 6379
- Milvus: 19530
- MinIO: 9000/9001
- Attu: 8080

### 7.3 创建数据库

```bash
mysql -u root -p123456 -e "CREATE DATABASE IF NOT EXISTS langchain_app;"
```

### 7.4 启动应用

```bash
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 7.5 访问

- 前端: http://127.0.0.1:8000/
- API 文档: http://127.0.0.1:8000/docs

---

## 八、API 调用示例

### 8.1 注册

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "123456"}'
```

### 8.2 登录

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "123456"}'
```

### 8.3 流式聊天

```bash
curl -X POST http://127.0.0.1:8000/chat/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "什么是 LangChain？"}'
```

---

## 九、目录结构

```
SuperMew/
├── backend/
│   ├── __init__.py
│   ├── app.py           # FastAPI 入口
│   ├── api.py          # API 路由
│   ├── auth.py         # 认证鉴权
│   ├── agent.py        # Agent 核心
│   ├── rag_pipeline.py # RAG 工作流
│   ├── rag_utils.py    # RAG 工具函数
│   ├── embedding.py    # 向量化服务
│   ├── milvus_client.py # Milvus 客户端
│   ├── milvus_writer.py # 向量写入
│   ├── document_loader.py # 文档加载
│   ├── parent_chunk_store.py # 父块存储
│   ├── models.py       # ORM 模型
│   ├── schemas.py      # Pydantic 模型
│   ├── database.py     # 数据库配置
│   ├── cache.py        # Redis 缓存
│   └── tools.py        # 自定义工具
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── data/
│   └── documents/      # 上传文档
├── docker-compose.yml
├── pyproject.toml
├── .env
└── README.md
```

---

## 十、注意事项

1. **LLM 替换**: 当前使用阿里云 DashScope（OpenAI 兼容），可替换为 OpenAI、Claude 等
2. **向量库**: 当前使用 Milvus，可替换为 Qdrant、Chroma 等
3. **数据库**: 已改为 MySQL（通过 pymysql），如需 PostgreSQL 改回 psycopg2
4. **生产环境**: 需要修改 `JWT_SECRET_KEY`、配置 HTTPS、添加限流等
