'''
@create_time: 2026/3/30
@Author: GeChao
@File: db_chat_message.py
'''
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class ChatMessage(Base):
    __tablename__ = "db_chat_message"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_ref_id = Column(Integer, ForeignKey("db_chat_session.id", ondelete="CASCADE"), nullable=False, index=True)
    message_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    rag_trace = Column(JSON, nullable=True)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)

    session = relationship("ChatSession", back_populates="messages")
