'''
@create_time: 2026/3/30
@Author: GeChao
@File: db_chat_session.py
'''
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class ChatSession(Base):
    __tablename__ = "db_chat_session"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("db_user.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(120), nullable=False, index=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)
    create_user = Column(String(128), nullable=False, default="system")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    update_user = Column(String(128), nullable=False, default="system")

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
