'''
@create_time: 2026/02/17
@Author: GeChao
@File: db_user.py
'''
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "db_user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)
    create_user = Column(String(128), nullable=False, default="system")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    update_user = Column(String(128), nullable=False, default="system")

    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
