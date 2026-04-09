- # AGENTS.md

  ## 项目说明

  这是一个前后端分离的 Agentic RAG 项目，目标是提供基于知识库的问答能力，支持认证、会话管理、文档上传检索、SSE 流式回答以及可观测追踪。

  项目开发时，必须优先保持现有分层清晰、接口行为稳定、RAG 链路可追踪，不要为了小需求破坏整体结构。

  ---

  ## 目录约定

  ### 根目录
  - `backend/`：后端服务
  - `frontend/`：前端应用

  ### 后端目录
  - `backend/app/main.py`：FastAPI 应用入口、路由挂载、中间件
  - `backend/app/agent.py`：Agent 核心逻辑
  - `backend/app/tools.py`：Agent 工具暴露与上下文桥接
  - `backend/app/rag_pipeline.py`：LangGraph RAG 流程编排
  - `backend/app/rag_utils.py`：检索、重排、融合、分块等算法实现
  - `backend/app/routes/`：接口层
  - `backend/app/services/`：业务编排层
  - `backend/app/models/`：数据库 ORM 模型
  - `backend/app/schemas/`：请求/响应数据结构
  - `backend/app/utils/`：通用工具
  - `backend/app/database.py`：数据库连接与 Session 管理
  - `backend/app/config.py`：配置与日志

  ### 前端目录
  - `frontend/src/main.js`：前端入口
  - `frontend/src/App.vue`：应用根组件
  - `frontend/src/router/index.js`：路由配置
  - `frontend/src/views/`：页面视图
  - `frontend/src/services/`：接口调用层
  - `frontend/src/config.js`：前端配置
  - `frontend/src/state.js`：状态管理
  - `frontend/src/style.css`：全局样式

  ---

  ## 后端开发规则

  ### 1. 分层职责必须清晰
  - `routes/*` 只负责 HTTP 层工作：入参接收、鉴权、调用 service、返回响应。
  - `services/*` 负责业务流程编排，不要把复杂流程堆在 route 里。
  - `schemas/*` 负责 API 输入输出结构。
  - `models/*` 负责 ORM 数据模型。
  - `tools.py` 负责 Agent 工具暴露，不要把完整业务流程直接塞进工具层。
  - `rag_pipeline.py` 负责 LangGraph 节点与流程路由。
  - `rag_utils.py` 负责检索算法、重排、融合、上下文处理。

  ### 2. 不要混杂职责
  不要把下面几类逻辑写进同一个超长函数：
  - 请求解析
  - RAG 编排
  - 数据库写入
  - SSE 输出
  - 响应拼装

  ### 3. 变更接口时要同步检查
  修改任一接口时，默认同步检查：
  - route
  - service
  - schema
  - model
  - 前端 services 调用层
  - 前端页面渲染与状态处理

  ### 4. 保持最小改动
  - 优先局部修复或局部新增
  - 不做无关重构
  - 不随意重命名现有 API、字段名、事件名
  - 不随意新增依赖，除非任务明确需要

  ---

  ## RAG / Agent 相关规则

  ### 1. 保持现有链路边界
  当前核心链路大致为：
  - 前端发起 REST / SSE 请求
  - FastAPI 路由进入 chat/document/auth 模块
  - Agent 调用 `search_knowledge_base`
  - `tools.py` 调用 RAG pipeline
  - `rag_pipeline.py` 组织 LangGraph 节点
  - `rag_utils.py` 执行检索、重排、融合、分块扩展
  - 检索结果返回 Agent
  - 后端以 SSE 形式输出内容、rag_step、trace、[DONE]

  修改相关逻辑时，优先保持这条链路清晰，不要把检索逻辑直接散落到 route 或前端。

  ### 2. SSE 行为必须稳定
  如果任务涉及 `/chat/stream` 或类似流式接口：
  - 保持 SSE 事件格式稳定
  - 不要随意改动 `content`、`rag_step`、`trace`、`[DONE]` 这类事件语义
  - 若必须调整，必须明确说明对前端渲染的影响

  ### 3. rag_trace 与可追溯性不能丢
  凡是修改检索链路、重排逻辑、扩展检索逻辑时：
  - 需要考虑 `rag_trace` 是否仍然完整
  - 需要考虑前端是否还能展示追踪信息
  - 需要考虑落库逻辑是否仍一致

  ### 4. 检索相关改动优先局部化
  涉及以下内容时，优先限定改动范围，不要整段重写：
  - hybrid/dense retrieval
  - rerank
  - RRF fuse
  - dedupe
  - auto-merge
  - grade_documents
  - rewrite_question

  ---

  ## 前端开发规则

  ### 1. 前端职责
  前端负责：
  - 页面展示
  - 状态管理
  - 表单交互
  - SSE 流式内容渲染
  - trace / progress 展示
  - 调用后端 API

  复杂业务规则、检索策略、Agent 编排逻辑应放在后端，不要硬编码到前端组件中。

  ### 2. 前端代码组织
  - 页面逻辑优先放在 `views/`
  - 接口请求优先收敛到 `services/`
  - 路由逻辑放在 `router/`
  - 全局配置放在 `config.js`
  - 状态相关逻辑放在 `state.js`

  不要把“页面渲染 + 网络请求 + 状态处理 + 数据转换”全部塞进一个组件里。

  ### 3. 联调规则
  当后端请求参数、响应字段、SSE 事件、trace 结构发生变化时：
  - 前端调用层必须同步修改
  - 页面渲染逻辑必须同步检查
  - loading / streaming / success / error 状态必须同步验证

  ---

  ## 认证、会话与文档管理规则

  ### 1. 认证逻辑
  涉及 `auth` 路由或用户信息时：
  - 保持鉴权流程一致
  - 不要随意改变 token 返回结构
  - 不要在前端硬编码用户身份逻辑

  ### 2. 会话逻辑
  涉及会话列表、会话详情、会话删除时：
  - 保持 session 结构稳定
  - 注意会话与消息落库是否一致
  - 注意前端会话切换是否受影响

  ### 3. 文档管理
  涉及文档上传、删除、检索时：
  - 注意文档元数据与向量写入链路的一致性
  - 注意 Milvus、MySQL、Redis 的联动影响
  - 不要只改上传接口而忽略后续检索结果结构

  ---

  ## 环境与常用命令

  ### 后端
  - 安装依赖：`pip install -r requirements.txt`
  - 启动依赖服务：`docker compose up -d`
  - 启动后端：`uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

  ### 前端
  - 安装依赖：`npm install`
  - 启动前端：`npm run dev`

  ### 开发要求
  - 修改后端代码时，优先做最小必要验证
  - 修改前端代码时，至少验证页面加载、请求调用、状态切换、SSE 渲染
  - 如果没有自动化测试，也要提供明确的手动验证步骤

  ---

  ## 禁止事项

  - 不要修改 `.env`、密钥或生产配置，除非任务明确要求
  - 不要为了小需求重构整个 RAG pipeline
  - 不要在 `routes/*` 中堆积大段业务逻辑
  - 不要在前端组件中硬编码复杂检索规则
  - 不要随意改动 API 前缀、SSE 协议格式、trace 输出结构
  - 不要未经说明就修改数据库字段、消息结构或会话结构

  ---

  ## 输出要求

  完成任务时，请明确说明：
  1. 修改了哪些文件
  2. 每个文件为什么改
  3. 是否影响 API 结构
  4. 是否影响 SSE 事件格式
  5. 是否影响前端联调
  6. 是否影响 RAG trace 或检索链路
  7. 风险点和后续注意事项

  ---

  ## 完成标准

  只有同时满足以下条件，任务才算完成：
  - 改动符合现有前后端分层
  - route / service / schema / model / frontend service 职责仍清晰
  - RAG / Agent 链路仍可解释、可追踪
  - 若涉及流式输出，SSE 行为保持稳定
  - 若涉及前后端联动，影响已说明清楚
  - 改动可 review、可验证、可维护
