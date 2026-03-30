'''
@create_time: 2026/3/30
@Author: GeChao
@File: db_parent_chunk.py
'''
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.database import Base


class ParentChunk(Base):
    __tablename__ = "db_parent_chunk"

    chunk_id = Column(String(512), primary_key=True)
    text = Column(Text, nullable=False)
    filename = Column(String(255), nullable=False, index=True)
    file_type = Column(String(50), default="", nullable=False)
    file_path = Column(String(1024), default="", nullable=False)
    page_number = Column(Integer, default=0, nullable=False)
    parent_chunk_id = Column(String(512), default="", nullable=False)
    root_chunk_id = Column(String(512), default="", nullable=False)
    chunk_level = Column(Integer, default=0, nullable=False)
    chunk_idx = Column(Integer, default=0, nullable=False)
    create_time = Column(DateTime, server_default=func.now(), nullable=False)
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
