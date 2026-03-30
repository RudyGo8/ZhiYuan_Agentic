'''
@create_time: 2026/3/30
@Author: GeChao
@File: chat_service.py
'''
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.db_user import User
from app.models.db_chat_session import ChatSession
from app.models.db_chat_message import ChatMessage
from app.services.rag_service import rag_service
from app.config import ARK_API_KEY, MODEL, BASE_URL
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage


class ChatService:
    @staticmethod
    def save_message(user_id: str, session_id: str, message_type: str, content: str, rag_trace: dict = None):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return False

            session = db.query(ChatSession).filter(
                ChatSession.user_id == user.id,
                ChatSession.session_id == session_id
            ).first()
            if not session:
                session = ChatSession(user_id=user.id, session_id=session_id, metadata_json={})
                db.add(session)
                db.commit()
                db.refresh(session)

            message = ChatMessage(
                session_ref_id=session.id,
                message_type=message_type,
                content=content,
                rag_trace=rag_trace
            )
            db.add(message)
            session.update_time = datetime.now()
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def get_session_messages(user_id: str, session_id: str):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return []

            session = db.query(ChatSession).filter(
                ChatSession.user_id == user.id,
                ChatSession.session_id == session_id
            ).first()
            if not session:
                return []

            messages = db.query(ChatMessage).filter(
                ChatMessage.session_ref_id == session.id
            ).order_by(ChatMessage.id.asc()).all()

            return [
                {
                    "type": msg.message_type,
                    "content": msg.content,
                    "timestamp": msg.create_time.isoformat() if msg.create_time else "",
                    "rag_trace": msg.rag_trace
                }
                for msg in messages
            ]
        finally:
            db.close()

    @staticmethod
    def get_session_list(user_id: str):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return []

            sessions = db.query(ChatSession).filter(
                ChatSession.user_id == user.id
            ).order_by(ChatSession.update_time.desc()).all()

            result = []
            for s in sessions:
                count = db.query(ChatMessage).filter(ChatMessage.session_ref_id == s.id).count()
                result.append({
                    "session_id": s.session_id,
                    "updated_at": s.update_time.isoformat() if s.update_time else "",
                    "message_count": count
                })
            return result
        finally:
            db.close()

    @staticmethod
    def delete_session(user_id: str, session_id: str):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return False

            session = db.query(ChatSession).filter(
                ChatSession.user_id == user.id,
                ChatSession.session_id == session_id
            ).first()
            if not session:
                return False

            db.delete(session)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def chat_with_rag(user_text: str, user_id: str, session_id: str) -> dict:
        messages = ChatService.get_session_messages(user_id, session_id)
        
        chat_history = []
        for msg in messages:
            if msg["type"] == "human":
                chat_history.append(HumanMessage(content=msg["content"]))
        
        docs = rag_service.retrieve(user_text, top_k=5)
        context = rag_service.format_context(docs)
        
        if context:
            prompt = f"""基于以下知识库内容回答用户问题。如果知识库中没有相关信息，请如实说明。

知识库内容:
{context}

用户问题: {user_text}

回答:"""
        else:
            prompt = user_text
        
        model = init_chat_model(
            model=MODEL,
            model_provider="openai",
            api_key=ARK_API_KEY,
            base_url=BASE_URL,
            temperature=0.3
        )
        
        chat_history.append(HumanMessage(content=prompt))
        
        try:
            response = model.invoke(chat_history)
            response_content = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            response_content = f"抱歉，处理您的请求时发生错误: {str(e)}"
        
        rag_trace = {"tool_used": bool(docs), "retrieved_docs": docs}
        
        ChatService.save_message(user_id, session_id, "human", user_text)
        ChatService.save_message(user_id, session_id, "ai", response_content, rag_trace)
        
        return {"response": response_content, "rag_trace": rag_trace}
