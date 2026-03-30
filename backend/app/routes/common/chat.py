'''
@create_time: 2026/3/30
@Author: GeChao
@File: chat.py
'''
from fastapi import APIRouter, Depends, HTTPException
from app.models.db_user import User
from app.schemas.auth import ChatRequest, ChatResponse, SessionMessagesResponse, SessionListResponse, SessionDeleteResponse, MessageInfo, SessionInfo
from app.utils.auth_utils import get_current_user
from app.services.chat_service import ChatService

router_r1 = APIRouter(
    prefix="/api/r1/chat",
    tags=["chat"]
)

chat_service = ChatService()


@router_r1.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user)):
    session_id = request.session_id or "default_session"
    result = chat_service.chat_with_rag(request.message, current_user.username, session_id)
    return ChatResponse(**result)


@router_r1.get("/sessions/{session_id}", response_model=SessionMessagesResponse)
async def get_session_messages(session_id: str, current_user: User = Depends(get_current_user)):
    messages = chat_service.get_session_messages(current_user.username, session_id)
    return SessionMessagesResponse(messages=[MessageInfo(**msg) for msg in messages])


@router_r1.get("/sessions", response_model=SessionListResponse)
async def list_sessions(current_user: User = Depends(get_current_user)):
    sessions = chat_service.get_session_list(current_user.username)
    return SessionListResponse(sessions=[SessionInfo(**s) for s in sessions])


@router_r1.delete("/sessions/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    deleted = chat_service.delete_session(current_user.username, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return SessionDeleteResponse(session_id=session_id, message="成功删除会话")
