'''
@create_time: 2025/10/21
@Author: GeChao
@File: database.py
'''
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD, MYSQL_DATABASE

import pymysql
pymysql.install_as_MySQLdb()

SQLALCHEMY_DATABASE_URL = f"mysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    pool_size=10,
    pool_recycle=3600,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models.db_user import User
    from app.models.db_chat_session import ChatSession
    from app.models.db_chat_message import ChatMessage
    from app.models.db_parent_chunk import ParentChunk
    Base.metadata.create_all(bind=engine)
