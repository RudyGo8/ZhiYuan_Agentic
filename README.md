# 知源助手（RAG Agent）项目总结

## 1. 项目概述
知源助手是一个基于 RAG（检索增强生成）的知识问答系统，支持：
- 用户注册/登录与权限区分（普通用户、管理员）
- 流式聊天（SSE）
- 会话历史管理
- 文档上传、向量化、检索问答
- 检索过程可视化（部分 trace 信息）

项目为前后端分离架构：
- `backend/`：FastAPI + LangChain/LangGraph + MySQL/Redis/Milvus
- `frontend/`：Vue 3 + Vite + Vue Router + Element Plus

---

## 2. 当前技术栈（以代码为准）
### 前端
- Vue 3
- Vite
- Vue Router
- Element Plus
- marked + highlight.js + DOMPurify（Markdown 渲染与安全消毒）

### 后端
- FastAPI
- SQLAlchemy
- LangChain / LangGraph
- MySQL
- Redis
- Milvus

---

## 3. 目录结构（核心）
```text
Rag_Agent/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ routes/common/
│  │  │  ├─ auth.py
│  │  │  ├─ chat.py
│  │  │  └─ document.py
│  │  ├─ services/
│  │  ├─ models/
│  │  ├─ schemas/
│  │  └─ utils/
│  ├─ docker-compose.yml
│  └─ requirements.txt
├─ frontend/
│  ├─ index.html
│  ├─ package.json
│  ├─ vite.config.js
│  ├─ .env.example
│  └─ src/
│     ├─ main.js
│     ├─ App.vue
│     ├─ router/index.js
│     ├─ views/RagWorkspace.vue
│     ├─ services/
│     │  ├─ api.js
│     │  └─ markdown.js
│     ├─ config.js
│     ├─ state.js
│     └─ style.css
└─ README.md
```

---

## 4. 前端工程化现状
前端已完成从“单文件脚本”到“Vite 工程”的迁移，当前特征：
- 入口标准化：`index.html -> src/main.js`
- 路由层接入：`App.vue` 仅保留 `RouterView`
- 页面层：主页面在 `views/RagWorkspace.vue`
- 服务层：`services/api.js`、`services/markdown.js`
- 配置层：`config.js` 支持环境变量 `VITE_API_BASE_URL`

默认配置：
- `VITE_API_BASE_URL=/api/r1`
- Vite 代理 `/api` 到 `http://127.0.0.1:8000`

---

## 5. 主要接口（前端实际调用）
统一前缀：`/api/r1`

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /chat/stream`（SSE）
- `GET /chat/sessions`
- `GET /chat/sessions/{sessionId}`
- `DELETE /chat/sessions/{sessionId}`
- `GET /documents`
- `POST /documents/upload`
- `DELETE /documents/{filename}`

---

## 6. 本地运行
## 6.1 后端
```bash
cd backend
pip install -r requirements.txt
docker compose up -d
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

常用地址：
- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

## 6.2 前端
```bash
cd frontend
npm install
npm run dev
```

默认前端地址：
- `http://127.0.0.1:5173`
---


