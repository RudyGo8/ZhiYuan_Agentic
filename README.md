# ZhiYuan Agent（Rag_Agent）

## 项目简介
这是一个前后端分离的 Agentic RAG 项目，提供基于知识库的问答能力。  
系统支持认证、会话管理、文档上传检索、SSE 流式回答、RAG Trace 追踪，以及可选 MCP 外部只读检索能力。

## 核心功能
- 用户认证：注册、登录、JWT 鉴权
- 会话管理：会话列表、会话详情、删除会话
- 文档管理：上传 PDF/Word/Excel 并向量化入库
- RAG 检索：混合检索（dense+sparse）、重排、查询扩展、自动合并上下文
- 流式对话：`/api/r1/chat/stream` SSE 输出 `content / rag_step / trace / [DONE]`
- 可追踪：消息落库时保存 `rag_trace`
- MCP（可选）：支持 `git`、`mysql` 等只读外部来源

## 目录结构
```text
Rag_Agent/
├─ backend/    # FastAPI + Agent + RAG + MCP
└─ frontend/   # Vue3 + Vite 前端
```

## 快速开始

### 1) 启动依赖服务（后端目录）
```bash
cd backend
docker compose up -d
```

### 2) 启动后端
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3) 启动前端
```bash
cd frontend
npm install
npm run dev
```

## 配置说明
后端配置文件：`backend/.env`

常用项（最少）：
- `ARK_API_KEY`
- `MODEL`
- `BASE_URL`
- `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USERNAME` / `MYSQL_PASSWORD` / `MYSQL_DATABASE`
- `REDIS_URL`
- `MILVUS_HOST` / `MILVUS_PORT` / `MILVUS_COLLECTION`

MCP 相关（可选）：
- `MCP_ENABLED=true|false`
- `MCP_SERVERS_JSON=...`
- `MCP_SOURCE_ALLOWLIST=git,mysql`
- `MCP_TOOL_ALLOWLIST=...`（可选）

## 基本使用
1. 登录系统（普通用户可聊天，管理员可管理文档）
2. 管理员上传文档到知识库
3. 在聊天区发起问题，前端通过 `/api/r1/chat/stream` 接收流式回答
4. 在消息中查看 `rag_step` 和 `trace`，追踪检索过程与证据来源

## 常用接口
- 认证
  - `POST /api/r1/auth/register`
  - `POST /api/r1/auth/login`
  - `GET /api/r1/auth/me`
- 聊天
  - `POST /api/r1/chat/stream`
  - `GET /api/r1/chat/sessions`
  - `GET /api/r1/chat/sessions/{session_id}`
  - `DELETE /api/r1/chat/sessions/{session_id}`
- 文档
  - `GET /api/r1/documents`
  - `POST /api/r1/documents/upload`
  - `DELETE /api/r1/documents/{filename}`

