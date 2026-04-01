"""
================================================================================
RAG Agent 主入口 - main.py
================================================================================
项目启动入口，FastAPI 应用配置

启动流程:
    1. 初始化数据库 (MySQL 表创建)
    2. 配置 CORS 中间件
    3. 注册日志中间件
    4. 注册路由 (Auth / Chat / Document)
    5. 挂载前端静态文件
    6. 启动 Uvicorn 服务器 (端口 8000)

API 路由前缀:
    - /api/r1/auth: 认证相关 (登录/注册)
    - /api/r1/chat: 聊天相关 (发送消息/获取会话)
    - /api/r1/documents: 文档管理 (上传/删除)
================================================================================
@create_time: 2026/3/30
@Author: GeChao
@File: main.py
"""
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from app.config import logger
from app.database import init_db
from app.routes.common.auth import router_r1 as auth_router_r1
from app.routes.common.chat import router_r1 as chat_router_r1
from app.routes.common.document import router_r1 as document_router_r1

# 前端静态文件目录 (项目根目录的 frontend 文件夹)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

# 创建 FastAPI 应用
app = FastAPI(title="RAG Agent API")


# ===============================================================================
# 启动事件 - 初始化数据库
# ===============================================================================
@app.on_event("startup")
async def startup_event():
    """
    ================================================================================
    [启动事件] startup_event
    ================================================================================
    功能: 应用启动时执行
        - 初始化 MySQL 数据库表 (创建 User / ChatSession / ChatMessage 等)
    
    调用: init_db() → Base.metadata.create_all(bind=engine)
    ================================================================================
    """
    init_db()


# ===============================================================================
# CORS 中间件配置
# ===============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================================================================
# 日志中间件 - 记录请求/响应
# ===============================================================================
@app.middleware('http')
async def log_request(request: Request, call_next):
    """
    ================================================================================
    [中间件] 日志记录
    ================================================================================
    功能: 记录每个 HTTP 请求和响应
        - 请求: method + url
        - 响应: status_code + url
    ================================================================================
    """
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code} {request.url}")
    return response


# ===============================================================================
# 注册路由
# ===============================================================================
# 认证路由: /api/r1/auth/*
app.include_router(auth_router_r1)

# 聊天路由: /api/r1/chat/*
app.include_router(chat_router_r1)

# 文档路由: /api/r1/documents/*
app.include_router(document_router_r1)


# ===============================================================================
# 挂载前端静态文件
# ===============================================================================
# 将 frontend 目录作为根路径静态文件服务
# 支持 SPA (Single Page Application) 路由
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ===============================================================================
# 主程序入口
# ===============================================================================
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
