'''
@create_time: 2026/3/30
@Author: GeChao
@File: chat.py
'''
from fastapi import APIRouter, Depends, HTTPException
from app.models.db_user import User
from app.schemas.auth import ChatRequest, ChatResponse, SessionMessagesResponse, SessionListResponse, SessionDeleteResponse, MessageInfo, SessionInfo
from app.utils.auth_utils import get_current_user
from app.agent import storage, chat_with_agent_stream, chat_with_agent

router_r1 = APIRouter(
    prefix="/api/r1/chat",
    tags=["chat"]
)


@router_r1.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    ================================================================================
    [路由] chat_endpoint - 非流式聊天
    ================================================================================
    流程:
        1. 验证用户身份 (JWT Token)
        2. 调用 chat_with_agent() 处理消息
        3. 返回响应结果
    ================================================================================
    """
    session_id = request.session_id or "default_session"
    # 调用 Agent 处理聊天
    result = chat_with_agent(request.message, current_user.username, session_id)
    return ChatResponse(**result)


@router_r1.post("/stream")
async def chat_stream_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    ================================================================================
    [路由] chat_stream_endpoint - 流式聊天 (SSE)
    ================================================================================
    流程:
        1. 验证用户身份 (JWT Token)
        2. 调用 chat_with_agent_stream() 获取生成器
        3. 使用 StreamingResponse 返回 SSE 流
    ================================================================================
    """
    from fastapi.responses import StreamingResponse
    
    session_id = request.session_id or "default_session"
    
    # 流式返回 (SSE)
    return StreamingResponse(
        chat_with_agent_stream(request.message, current_user.username, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router_r1.get("/sessions/{session_id}", response_model=SessionMessagesResponse)
async def get_session_messages(session_id: str, current_user: User = Depends(get_current_user)):
    """
    ================================================================================
    [路由] get_session_messages - 获取会话消息历史
    ================================================================================
    """
    messages = storage.get_session_messages(current_user.username, session_id)
    return SessionMessagesResponse(messages=[MessageInfo(**msg) for msg in messages])


@router_r1.get("/sessions", response_model=SessionListResponse)
async def list_sessions(current_user: User = Depends(get_current_user)):
    """
    ================================================================================
    [路由] list_sessions - 获取会话列表
    ================================================================================
    """
    sessions = storage.list_session_infos(current_user.username)
    return SessionListResponse(sessions=[SessionInfo(**s) for s in sessions])


@router_r1.delete("/sessions/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    """
    ================================================================================
    [路由] delete_session - 删除会话
    ================================================================================
    """
    deleted = storage.delete_session(current_user.username, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return SessionDeleteResponse(session_id=session_id, message="成功删除会话")
