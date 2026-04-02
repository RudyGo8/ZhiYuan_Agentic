# 知源助手：基于 Agentic RAG 的可追溯知识问答系统

## 一、项目概述

知源助手是一个基于 LangChain/LangGraph 的智能问答系统，支持 RAG（检索增强生成）、知识库管理、流式输出、实时思考链路展示、用户认证等功能。

**核心特性**：
- **Agentic RAG**：基于 LangGraph 的智能 Agent 编排，支持查询理解、文档检索、答案生成的全流程自动化
- **可追溯答案**：每个回答都能追溯到原始文档来源，确保答案可信可控
- **混合检索**：融合稠密向量与稀疏向量（BM25），提升检索召回率
- **流式输出**：实时流式返回答案，带有思考过程可视化
- **多级分块**：Auto-merging Retriever 实现上下文感知的文档分块

---

## 二、技术栈

### 2.1 后端核心

| 技术 | 用途 |
|------|------|
| **FastAPI** | Web 框架 |
| **LangChain** | LLM 应用框架 |
| **LangGraph** | Agent 状态图编排 |
| **LangSmith** | 可观测性/调试 |
| **SQLAlchemy** | ORM |

### 2.2 数据库与向量库

| 技术 | 用途 |
|------|------|
| **MySQL** | 持久化存储（用户、会话、消息、父文档） |
| **Redis** | 缓存层 |
| **Milvus** | 向量数据库（支持 Hybrid Search） |

### 2.3 前端

- **Vue 3** (CDN)
- **marked** - Markdown 渲染
- **highlight.js** - 代码高亮

---

## 三、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (Vue 3 CDN)                        │
│                  http://127.0.0.1:8000/                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼ SSE / HTTP
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI 后端 (8000)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  routes/        │  services/      │  models/            │  │
│  │  ├─ auth.py     │  ├─ chat_service│  ├─ db_user.py      │  │
│  │  ├─ chat.py     │  ├─ rag_service │  ├─ db_chat_session │  │
│  │  └─ document.py │                 │  ├─ db_chat_message│  │
│  │                 │                 │  └─ db_parent_chunk │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  utils/            │  agent.py      │  rag_pipeline.py   │  │
│  │  ├─ auth_utils.py │  Agent 核心    │  RAG 工作流        │  │
│  │  ├─ embedding_    │                │                    │  │
│  │  │   service.py   │                │                    │  │
│  │  ├─ milvus_      │                │                    │  │
│  │  │   service.py  │                │                    │  │
│  │  └─ document_    │                │                    │  │
│  │      loader.py   │                │                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│      MySQL      │  │     Redis       │  │    Milvus      │
│     (3307)      │  │    (6379)       │  │   (19530)      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │    LangChain / LangGraph      │
               │    Agent + RAG Pipeline       │
               └───────────────────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │    LLM (阿里云 DashScope)    │
               │    OpenAI 兼容 API            │
               └───────────────────────────────┘
```

---

## 四、目录结构

```
知源助手/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── agent.py             # Agent 核心逻辑
│   │   ├── rag_pipeline.py      # RAG 工作流 (LangGraph StateGraph)
│   │   ├── rag_utils.py         # RAG 工具函数
│   │   ├── cache.py             # Redis 缓存封装
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # 数据库配置
│   │   ├── milvus_writer.py     # Milvus 向量写入
│   │   ├── parent_chunk_store.py # 父级分块存储
│   │   ├── tools.py             # 自定义工具
│   │   ├── models/              # ORM 模型
│   │   │   ├── db_user.py       # 用户模型
│   │   │   ├── db_chat_session.py  # 会话模型
│   │   │   ├── db_chat_message.py  # 消息模型
│   │   │   └── db_parent_chunk.py # 父级分块模型
│   │   ├── routes/              # API 路由
│   │   │   └── common/
│   │   │       ├── auth.py      # 认证接口
│   │   │       ├── chat.py     # 聊天接口
│   │   │       └── document.py # 文档管理接口
│   │   ├── schemas/             # Pydantic 模型
│   │   │   └── auth.py
│   │   ├── services/            # 业务逻辑
│   │   │   ├── chat_service.py  # 聊天服务
│   │   │   └── rag_service.py   # RAG 服务
│   │   ├── utils/               # 工具函数
│   │   │   ├── auth_utils.py   # JWT 认证工具
│   │   │   ├── document_loader.py  # 文档加载与分块
│   │   │   ├── embedding_service.py # 向量化服务
│   │   │   └── milvus_service.py    # Milvus 客户端
│   │   └── test_api/            # 测试代码
│   │       ├── test_api.py
│   │       └── test_rag_units.py
│   ├── .env                     # 环境变量
│   ├── docker-compose.yml       # Docker 编排 (MySQL, Redis, Milvus)
│   ├── requirements.txt         # Python 依赖
│   └── data/                    # 文档数据
│       └── test_docs/           # 测试文档
├── frontend/
│   ├── index.html               # 前端页面
│   ├── script.js                # 前端脚本
│   └── style.css                # 样式文件
├── .gitignore
└── README.md
```

---

## 五、核心模块说明

### 5.1 backend/app/main.py

FastAPI 应用入口：
- CORS 中间件配置
- 静态文件挂载（前端）
- 数据库初始化
- 路由注册

### 5.2 backend/app/agent.py

LangChain Agent 核心：
- `chat_with_agent()` - 非流式对话
- `chat_with_agent_stream()` - 流式输出
- 会话记忆管理
- 消息摘要压缩

### 5.3 backend/app/rag_pipeline.py

RAG 工作流（LangGraph StateGraph）：
- **retrieve_initial**: 初次检索（Hybrid Search）
- **grade_documents**: 相关性评估
- **rewrite_question**: 查询重写（Step-back / HyDE）
- **retrieve_expanded**: 扩展检索

### 5.4 backend/app/routes/common/

API 路由层：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/auth/register` | POST | 用户注册 |
| `/auth/login` | POST | 用户登录 |
| `/auth/me` | GET | 获取当前用户 |
| `/sessions` | GET | 获取会话列表 |
| `/sessions/{id}` | GET | 获取会话消息 |
| `/sessions/{id}` | DELETE | 删除会话 |
| `/chat` | POST | 非流式聊天 |
| `/chat/stream` | POST | 流式聊天（SSE） |
| `/documents` | GET | 文档列表 |
| `/documents/upload` | POST | 上传文档 |
| `/documents/{filename}` | DELETE | 删除文档 |

### 5.5 backend/app/services/

- **chat_service.py**: 聊天业务逻辑
- **rag_service.py**: RAG 核心服务

### 5.6 backend/app/models/

SQLAlchemy ORM 模型：
- `db_user.py` - 用户表
- `db_chat_session.py` - 会话表
- `db_chat_message.py` - 消息表
- `db_parent_chunk.py` - 父级分块表

### 5.7 backend/app/utils/

- **auth_utils.py**: JWT 认证工具
- **document_loader.py**: 文档加载与分块
- **embedding_service.py**: 向量化服务
- **milvus_service.py**: Milvus 客户端

---

## 六、环境变量 (.env)

```env
# ===== 模型 =====
ARK_API_KEY=your_api_key
MODEL=qwen-plus
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDER=qwen-plus

# ===== Milvus =====
MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION=embeddings_collection

# ===== 数据库 / 缓存 =====
DATABASE_URL=mysql+pymysql://root:123456@127.0.0.1:3307/langchain_app
REDIS_URL=redis://127.0.0.1:6379/0

# ===== 认证 =====
JWT_SECRET_KEY=your-secret-key
ADMIN_INVITE_CODE=rudy_admin
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

---

## 七、运行指南

### 7.1 依赖安装

```bash
cd backend
pip install -r requirements.txt
```

### 7.2 启动中间件

```bash
cd backend
docker compose up -d
```

启动：
- MySQL: 3307（映射到 3306）
- Redis: 6379
- Milvus: 19530
- Milvus Attu (Web UI): 8080

### 7.3 启动应用

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7.4 访问

- 前端: http://127.0.0.1:8000/
- API 文档: http://127.0.0.1:8000/docs
- Milvus Attu: http://127.0.0.1:8080

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

## 九、技术细节

### 9.1 RAG 工作流

系统采用 LangGraph 实现的多阶段 RAG 流程：

1. **查询理解**：分析用户问题，提取关键实体
2. **混合检索**：结合向量相似度与 BM25 关键词匹配
3. **相关性评估**：使用 LLM 判断文档与问题的相关性
4. **查询重写**：如检索结果不佳，自动重写问题（Step-back / HyDE）
5. **答案生成**：基于检索结果生成最终答案

### 9.2 可追溯性

每个答案都会附带来源信息，用户可以点击查看原文。

---

## 十、注意事项

1. **LLM 替换**: 当前使用阿里云 DashScope（OpenAI 兼容），可替换为 OpenAI、Claude 等
2. **向量库**: 当前使用 Milvus，可替换为 Qdrant、Chroma 等
3. **生产环境**: 需要修改 `JWT_SECRET_KEY`、配置 HTTPS、添加限流等

---

## 十一、依赖版本

```
fastapi>=0.115.0
uvicorn>=0.30.0
langchain>=0.2.14
langgraph>=0.2.31
pymilvus>=2.4.0
sqlalchemy>=2.0.36
pymysql>=1.1.0
redis>=5.2.1
jieba>=0.0.0
langsmith>=0.0.0
```